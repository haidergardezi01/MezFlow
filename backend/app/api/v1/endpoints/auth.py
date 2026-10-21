from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user, require_roles
from app.core.config import settings
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User, UserProfile, UserRole
from app.models.audit import AuditLog
from app.models.restaurant import Restaurant
from app.schemas.auth import (
    UserSignupRequest,
    UserLoginPasswordRequest,
    OTPRequest,
    OTPVerifyLoginRequest,
    TokenResponse,
    UserProfileUpdate,
    UserProfileResponse,
    UserResponse,
    AuditLogResponse,
)
from app.services.otp import OTPService
from app.services.audit import record_audit_log

router = APIRouter()


def _get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def signup(
    data: UserSignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Registers a new user (Customer or Staff) under a restaurant.
    (FR-M1-01, FR-M1-05)
    """
    # 1. Verify restaurant exists
    rest_res = await db.execute(select(Restaurant).where(Restaurant.id == data.restaurant_id))
    if not rest_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found.",
        )

    # 2. Check for existing user in this restaurant
    conditions = []
    if data.email:
        conditions.append(User.email == data.email)
    if data.phone_number:
        conditions.append(User.phone_number == data.phone_number)

    if not conditions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone number must be provided.",
        )

    stmt = select(User).where(User.restaurant_id == data.restaurant_id, or_(*conditions))
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email or phone number already exists for this restaurant.",
        )

    # 3. Hash password
    if not data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for signup.",
        )
    hashed_pwd = get_password_hash(data.password)

    # 4. Create User & Profile
    new_user = User(
        restaurant_id=data.restaurant_id,
        email=data.email,
        phone_number=data.phone_number,
        hashed_password=hashed_pwd,
        role=data.role or UserRole.CUSTOMER,
        is_active=True,
        is_verified=False,
    )
    db.add(new_user)
    await db.flush()

    profile = UserProfile(
        user_id=new_user.id,
        display_name=data.display_name,
        preferred_language=data.preferred_language,
        push_notifications_enabled=True,
    )
    db.add(profile)
    await db.flush()

    # 5. Record Audit Log
    ip = _get_client_ip(request)
    await record_audit_log(
        db=db,
        restaurant_id=data.restaurant_id,
        user_id=new_user.id,
        action="USER_SIGNUP",
        resource_type="user",
        resource_id=str(new_user.id),
        details={"role": new_user.role.value, "display_name": data.display_name},
        ip_address=ip,
    )
    await db.commit()

    # 6. Generate Token
    token = create_access_token(
        subject=str(new_user.id),
        claims={
            "role": new_user.role.value,
            "restaurant_id": str(data.restaurant_id),
        },
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=new_user.role.value,
        restaurant_id=data.restaurant_id,
        user_id=new_user.id,
        display_name=profile.display_name,
        preferred_language=profile.preferred_language,
    )


@router.post("/login", response_model=TokenResponse, tags=["Authentication"])
async def login(
    data: UserLoginPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates a user using email/phone and password.
    (FR-M1-01, FR-M1-02, FR-M1-05)
    """
    clean_username = data.username.strip()
    stmt = (
        select(User)
        .options(selectinload(User.profile))
        .where(
            User.restaurant_id == data.restaurant_id,
            or_(
                User.email == clean_username,
                User.phone_number == clean_username,
            ),
        )
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    # Record Audit Log
    ip = _get_client_ip(request)
    await record_audit_log(
        db=db,
        restaurant_id=user.restaurant_id,
        user_id=user.id,
        action="USER_LOGIN_PASSWORD",
        resource_type="session",
        resource_id=str(user.id),
        details={"role": user.role.value},
        ip_address=ip,
    )
    await db.commit()

    token = create_access_token(
        subject=str(user.id),
        claims={
            "role": user.role.value,
            "restaurant_id": str(user.restaurant_id),
        },
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role.value,
        restaurant_id=user.restaurant_id,
        user_id=user.id,
        display_name=user.profile.display_name if user.profile else None,
        preferred_language=user.profile.preferred_language if user.profile else "en",
    )


@router.post("/request-otp", tags=["Authentication"])
async def request_otp(data: OTPRequest):
    """
    Requests a 6-digit one-time password sent to phone or email.
    (FR-M1-01)
    """
    clean_destination = data.destination.strip().lower()
    code = await OTPService.request_otp(clean_destination)
    return {
        "message": "One-time password dispatched successfully.",
        "destination": clean_destination,
        # For development / testing convenience, include code in debug mode
        "debug_otp": code if settings.DEBUG else None,
    }


@router.post("/verify-otp", response_model=TokenResponse, tags=["Authentication"])
async def verify_otp(
    data: OTPVerifyLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Verifies OTP code and authenticates the user.
    Creates account automatically if it does not yet exist.
    (FR-M1-01, FR-M1-02)
    """
    is_valid = await OTPService.verify_otp(data.destination, data.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code.",
        )

    clean_dest = data.destination.strip()
    is_email = "@" in clean_dest

    stmt = (
        select(User)
        .options(selectinload(User.profile))
        .where(
            User.restaurant_id == data.restaurant_id,
            or_(
                User.email == clean_dest,
                User.phone_number == clean_dest,
            ),
        )
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        # Create user verified by OTP
        user = User(
            restaurant_id=data.restaurant_id,
            email=clean_dest if is_email else None,
            phone_number=clean_dest if not is_email else None,
            hashed_password=get_password_hash("otp-auto-gen-password"),
            role=UserRole.CUSTOMER,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()

        profile = UserProfile(
            user_id=user.id,
            display_name=f"Guest {clean_dest[-4:]}",
            preferred_language="en",
            push_notifications_enabled=True,
        )
        db.add(profile)
        await db.flush()
    else:
        user.is_verified = True
        await db.flush()

    ip = _get_client_ip(request)
    await record_audit_log(
        db=db,
        restaurant_id=data.restaurant_id,
        user_id=user.id,
        action="USER_LOGIN_OTP",
        resource_type="session",
        resource_id=str(user.id),
        details={"destination": clean_dest},
        ip_address=ip,
    )
    await db.commit()

    token = create_access_token(
        subject=str(user.id),
        claims={
            "role": user.role.value,
            "restaurant_id": str(user.restaurant_id),
        },
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role.value,
        restaurant_id=user.restaurant_id,
        user_id=user.id,
        display_name=user.profile.display_name if user.profile else None,
        preferred_language=user.profile.preferred_language if user.profile else "en",
    )


@router.get("/me", response_model=UserResponse, tags=["Authentication"])
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the authenticated user details and profile.
    (FR-M1-02, FR-M1-03)
    """
    return current_user


@router.post("/refresh", response_model=TokenResponse, tags=["Authentication"])
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refreshes an active session token before expiration.
    (FR-M1-02)
    """
    token = create_access_token(
        subject=str(current_user.id),
        claims={
            "role": current_user.role.value,
            "restaurant_id": str(current_user.restaurant_id),
        },
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=current_user.role.value,
        restaurant_id=current_user.restaurant_id,
        user_id=current_user.id,
        display_name=current_user.profile.display_name if current_user.profile else None,
        preferred_language=current_user.profile.preferred_language if current_user.profile else "en",
    )


@router.patch("/profile", response_model=UserProfileResponse, tags=["Authentication"])
async def update_profile(
    data: UserProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates user display name, preferred language (English or Urdu), and notification preferences.
    (FR-M1-04, NFR-12)
    """
    profile = current_user.profile
    if not profile:
        profile = UserProfile(
            user_id=current_user.id,
            display_name=data.display_name or "User",
            preferred_language=data.preferred_language or "en",
            push_notifications_enabled=True,
        )
        db.add(profile)
    else:
        if data.display_name is not None:
            profile.display_name = data.display_name
        if data.preferred_language is not None:
            profile.preferred_language = data.preferred_language
        if data.push_notifications_enabled is not None:
            profile.push_notifications_enabled = data.push_notifications_enabled

    ip = _get_client_ip(request)
    await record_audit_log(
        db=db,
        restaurant_id=current_user.restaurant_id,
        user_id=current_user.id,
        action="PROFILE_UPDATED",
        resource_type="user_profile",
        resource_id=str(profile.id),
        details=data.model_dump(exclude_unset=True),
        ip_address=ip,
    )
    await db.commit()
    await db.refresh(profile)

    return profile


@router.get("/audit-logs", response_model=List[AuditLogResponse], tags=["Administration"])
async def list_audit_logs(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_roles([UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists immutable audit log entries for the tenant restaurant.
    Restricted to Manager role only. (FR-M1-06, FR-M1-07, NFR-10)
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.restaurant_id == current_user.restaurant_id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(min(limit, 100))
    )
    result = await db.execute(stmt)
    return result.scalars().all()
