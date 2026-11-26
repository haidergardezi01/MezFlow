from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc, func
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_db,
    get_current_user,
    require_roles,
    enforce_tenant,
    security_bearer,
    verify_clerk_session_token,
    fetch_clerk_verified_email,
)
from app.core.config import settings
from app.core.security import get_password_hash, verify_password, create_access_token, hash_signup_code
from app.models.user import User, UserProfile, UserRole
from app.models.audit import AuditLog
from app.models.pending_registration import PendingRegistration
from app.models.restaurant import Restaurant
import re
import secrets
from app.models.table import Table, TableStatus
from app.models.menu import MenuCategory, MenuItem
from app.schemas.auth import (
    UserSignupRequest,
    StaffCreateRequest,
    UserLoginPasswordRequest,
    OTPRequest,
    OTPVerifyLoginRequest,
    TokenResponse,
    UserProfileUpdate,
    UserProfileResponse,
    UserResponse,
    AuditLogResponse,
    RestaurantRegisterRequest,
    ClerkRegisterRequest,
    SignupVerifyRequest,
    OnboardingRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services import notify
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

    # 4. Create User & Profile (Always force Customer role for public signup)
    new_user = User(
        restaurant_id=data.restaurant_id,
        email=data.email,
        phone_number=data.phone_number,
        hashed_password=hashed_pwd,
        role=UserRole.CUSTOMER,
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


@router.post("/staff", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Administration"])
async def create_staff(
    data: StaffCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Provisions a staff user (Manager, Kitchen, Service, Cashier) within the manager's tenant restaurant.
    Guarded strictly by Manager RBAC and tenant enforcement.
    (FR-M1-03, FR-M1-05, FR-M1-07, NFR-08)
    """
    # Cross-tenant guard
    enforce_tenant(data.restaurant_id, current_user)

    if data.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer accounts cannot be created via the staff provisioning endpoint.",
        )

    # Check for existing user in this restaurant
    stmt = select(User).where(
        User.restaurant_id == data.restaurant_id,
        or_(
            User.email == data.email,
            User.phone_number == data.phone_number if data.phone_number else False,
        ),
    )
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email or phone number already exists in this restaurant.",
        )

    hashed_pwd = get_password_hash(data.password)
    staff_user = User(
        restaurant_id=data.restaurant_id,
        email=data.email,
        phone_number=data.phone_number,
        hashed_password=hashed_pwd,
        role=data.role,
        is_active=True,
        is_verified=True,
    )
    db.add(staff_user)
    await db.flush()

    profile = UserProfile(
        user_id=staff_user.id,
        display_name=data.display_name,
        preferred_language=data.preferred_language,
        push_notifications_enabled=True,
    )
    db.add(profile)
    await db.flush()

    ip = _get_client_ip(request)
    await record_audit_log(
        db=db,
        restaurant_id=data.restaurant_id,
        user_id=current_user.id,
        action="STAFF_USER_CREATED",
        resource_type="user",
        resource_id=str(staff_user.id),
        details={"role": staff_user.role.value, "email": data.email, "display_name": data.display_name},
        ip_address=ip,
    )
    await db.commit()
    stmt = (
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == staff_user.id)
    )
    res = await db.execute(stmt)
    return res.scalar_one()


@router.get("/staff", response_model=List[UserResponse], tags=["Administration"])
async def list_staff(
    current_user: User = Depends(require_roles([UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all real staff members for the authenticated manager's restaurant workspace.
    """
    stmt = (
        select(User)
        .options(selectinload(User.profile))
        .where(
            User.restaurant_id == current_user.restaurant_id,
            User.role.in_([UserRole.MANAGER, UserRole.KITCHEN_STAFF, UserRole.SERVICE_STAFF, UserRole.CASHIER]),
        )
        .order_by(User.created_at.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/staff/seed-starter-team", response_model=List[UserResponse], tags=["Administration"])
async def seed_starter_team(
    current_user: User = Depends(require_roles([UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Provisions real starter team accounts (Chef, Waiter, Cashier) for the manager's restaurant workspace.
    """
    rest_res = await db.execute(select(Restaurant).where(Restaurant.id == current_user.restaurant_id))
    rest = rest_res.scalar_one_or_none()
    slug = rest.slug if rest else "workspace"

    starter_roles = [
        (f"chef.{slug}@mezflow.com", f"{rest.name if rest else 'Kitchen'} Head Chef", UserRole.KITCHEN_STAFF),
        (f"waiter.{slug}@mezflow.com", f"{rest.name if rest else 'Floor'} Captain", UserRole.SERVICE_STAFF),
        (f"cashier.{slug}@mezflow.com", f"{rest.name if rest else 'Front'} Cashier", UserRole.CASHIER),
    ]

    for s_email, s_name, s_role in starter_roles:
        existing = await db.execute(
            select(User).where(User.restaurant_id == current_user.restaurant_id, User.email == s_email)
        )
        if not existing.scalar_one_or_none():
            u = User(
                restaurant_id=current_user.restaurant_id,
                email=s_email,
                # Never the manager's own password: that would let any cook log in as manager.
                hashed_password=get_password_hash(secrets.token_urlsafe(24)),
                role=s_role,
                is_active=True,
                is_verified=True,
            )
            db.add(u)
            await db.flush()
            p = UserProfile(
                user_id=u.id,
                display_name=s_name,
                preferred_language="en",
                push_notifications_enabled=True,
            )
            db.add(p)
            await db.flush()

    await db.commit()

    stmt = (
        select(User)
        .options(selectinload(User.profile))
        .where(
            User.restaurant_id == current_user.restaurant_id,
            User.role.in_([UserRole.MANAGER, UserRole.KITCHEN_STAFF, UserRole.SERVICE_STAFF, UserRole.CASHIER]),
        )
        .order_by(User.created_at.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/login", response_model=TokenResponse, tags=["Authentication"])
async def login(
    data: UserLoginPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates a user using email/phone and password.
    Supports global staff login (auto-resolving restaurant) or scoped restaurant login.
    (FR-M1-01, FR-M1-02, FR-M1-05)
    """
    clean_username = data.username.strip()

    if data.restaurant_id:
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .where(
                User.restaurant_id == data.restaurant_id,
                or_(
                    func.lower(User.email) == clean_username.lower(),
                    User.phone_number == clean_username,
                ),
            )
        )
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
    else:
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .where(
                or_(
                    func.lower(User.email) == clean_username.lower(),
                    User.phone_number == clean_username,
                ),
            )
        )
        res = await db.execute(stmt)
        users = res.scalars().all()
        if len(users) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple restaurant accounts match this username. Please specify restaurant_id.",
            )
        user = users[0] if users else None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect. Please check both and try again.",
        )

    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account was registered via OTP and does not have a password set. Please use OTP login.",
        )

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect. Please check both and try again.",
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
        # For development / testing convenience, include code ONLY in local development with DEBUG enabled
        "debug_otp": code if (settings.ENVIRONMENT == "development" and settings.DEBUG) else None,
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
    is_valid, error_msg = await OTPService.verify_otp(data.destination, data.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg or "Invalid or expired OTP code.",
        )

    clean_dest = data.destination.strip()
    is_email = "@" in clean_dest

    # Resolve target restaurant and existing user
    if data.restaurant_id:
        target_restaurant_id = data.restaurant_id
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .where(
                User.restaurant_id == target_restaurant_id,
                or_(
                    func.lower(User.email) == clean_dest.lower(),
                    User.phone_number == clean_dest,
                ),
            )
        )
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
    else:
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .where(
                or_(
                    func.lower(User.email) == clean_dest.lower(),
                    User.phone_number == clean_dest,
                ),
            )
        )
        res = await db.execute(stmt)
        users = res.scalars().all()
        if len(users) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple restaurant accounts match this destination. Please specify restaurant_id.",
            )
        user = users[0] if users else None
        if user:
            target_restaurant_id = user.restaurant_id
        else:
            rest_res = await db.execute(select(Restaurant).where(Restaurant.is_active == True).limit(1))
            default_rest = rest_res.scalar_one_or_none()
            if not default_rest:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active restaurant found. Please provide restaurant_id.",
                )
            target_restaurant_id = default_rest.id

    # Security check: OTP is strictly for Customers, not Staff or Managers
    if user and user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff and management accounts cannot authenticate using customer OTP. Please use staff password login.",
        )

    if not user:
        # Create user verified by OTP with NO usable password
        user = User(
            restaurant_id=target_restaurant_id,
            email=clean_dest if is_email else None,
            phone_number=clean_dest if not is_email else None,
            hashed_password=None,  # OTP accounts have no usable password; must authenticate via OTP
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
        restaurant_id=target_restaurant_id,
        user_id=user.id,
        action="USER_LOGIN_OTP",
        resource_type="session",
        resource_id=str(user.id),
        details={"destination": clean_dest},
        ip_address=ip,
    )
    await db.commit()

    # Eagerly load user with profile
    stmt = (
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == user.id)
    )
    res = await db.execute(stmt)
    user_loaded = res.scalar_one()

    token = create_access_token(
        subject=str(user_loaded.id),
        claims={
            "role": user_loaded.role.value,
            "restaurant_id": str(user_loaded.restaurant_id),
        },
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user_loaded.role.value,
        restaurant_id=user_loaded.restaurant_id,
        user_id=user_loaded.id,
        display_name=user_loaded.profile.display_name if user_loaded.profile else None,
        preferred_language=user_loaded.profile.preferred_language if user_loaded.profile else "en",
    )


@router.post(
    "/forgot-password",
    tags=["Authentication"],
    summary="Request a password reset OTP code (prints directly to terminal)",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validates that the user exists in PostgreSQL, generates a 6-digit OTP in Redis,
    and prints it prominently to the backend terminal for local verification.
    """
    clean_email = data.email.strip().lower()

    # 1. Verify user exists in PostgreSQL
    # Prefer the manager when one e-mail exists in several restaurants (scalar_one_or_none would 500 there)
    stmt = select(User).where(func.lower(User.email) == clean_email).order_by(desc(User.role == UserRole.MANAGER)).limit(1)
    res = await db.execute(stmt)
    user = res.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No account found with email '{clean_email}'.",
        )

    # 2. Generate and cache 6-digit OTP
    code = await OTPService.request_otp(f"reset:{clean_email}")

    # 3. Print prominently to terminal
    print("\n" + "=" * 60, flush=True)
    print(f"🔑 [MEZFLOW PASSWORD RESET OTP]", flush=True)
    print(f"📧 Account:       {clean_email}", flush=True)
    print(f"🔢 6-Digit OTP:   >>> {code} <<<", flush=True)
    print(f"⏳ Expiration:    5 minutes", flush=True)
    print("=" * 60 + "\n", flush=True)

    return {
        "success": True,
        "message": f"Verification code generated and printed to terminal for '{clean_email}'.",
        "email": clean_email,
        "debug_code": code if settings.ENVIRONMENT in ("development", "test") else None,
    }


@router.post(
    "/reset-password",
    response_model=TokenResponse,
    tags=["Authentication"],
    summary="Verify OTP and update user password",
)
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Verifies the 6-digit OTP code against Redis, updates the bcrypt password in PostgreSQL,
    and returns a fresh JWT authentication token.
    """
    clean_email = data.email.strip().lower()

    # 1. Verify OTP code
    is_valid, err_msg = await OTPService.verify_otp(f"reset:{clean_email}", data.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg or "Invalid or expired reset code.",
        )

    # 2. Fetch user
    stmt = (
        select(User)
        .options(selectinload(User.profile))
        .where(func.lower(User.email) == clean_email)
        .order_by(desc(User.role == UserRole.MANAGER))
        .limit(1)
    )
    res = await db.execute(stmt)
    user = res.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    # 3. Update password hash
    user.hashed_password = get_password_hash(data.new_password)
    user.updated_at = datetime.now(timezone.utc)

    # 4. Audit Log
    ip = _get_client_ip(request)
    if user.restaurant_id:
        await record_audit_log(
            db=db,
            restaurant_id=user.restaurant_id,
            user_id=user.id,
            action="PASSWORD_RESET_SUCCESS",
            resource_type="user",
            resource_id=str(user.id),
            details={"email": clean_email},
            ip_address=ip,
        )

    await db.commit()
    await db.refresh(user)

    # 5. Issue JWT Token
    token = create_access_token(
        subject=str(user.id),
        claims={
            "role": user.role.value,
            "restaurant_id": str(user.restaurant_id) if user.restaurant_id else None,
        },
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role.value,
        restaurant_id=user.restaurant_id,
        user_id=user.id,
        display_name=user.profile.display_name if user.profile else clean_email.split("@")[0],
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
    restaurant_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_roles([UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists immutable audit log entries for the tenant restaurant.
    Restricted to Manager role only. Enforces multi-tenant data isolation.
    (FR-M1-06, FR-M1-07, NFR-08, NFR-10)
    """
    if restaurant_id is not None:
        enforce_tenant(restaurant_id, current_user)

    target_restaurant_id = restaurant_id or current_user.restaurant_id
    stmt = (
        select(AuditLog)
        .where(AuditLog.restaurant_id == target_restaurant_id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(min(limit, 100))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


def _token_response(user: User, restaurant_id) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(
            subject=str(user.id),
            claims={"role": user.role.value, "restaurant_id": str(restaurant_id)},
        ),
        token_type="bearer",
        role=user.role.value,
        restaurant_id=restaurant_id,
        user_id=user.id,
        display_name=user.profile.display_name if user.profile else None,
        preferred_language=user.profile.preferred_language if user.profile else "en",
    )


async def _email_taken(db: AsyncSession, email: str) -> bool:
    res = await db.execute(select(User.id).where(func.lower(User.email) == email.lower()).limit(1))
    return res.first() is not None


ACCOUNT_EXISTS = "An account with this email already exists. Please sign in instead."


async def _provision_workspace(
    db: AsyncSession,
    request: Request,
    *,
    restaurant_name: str,
    manager_name: str,
    email: str,
    password_hash: str,
    currency: str = "PKR",
    phone: Optional[str] = None,
    address: Optional[str] = None,
    clerk_user_id: Optional[str] = None,
) -> User:
    """
    Provisions a new isolated multi-tenant restaurant workspace in PostgreSQL:
    restaurant with unique slug, manager account, starter team, 10 QR tables, starter menu.
    Callers must already have proven the e-mail (code or Clerk) and checked it is free.
    (FR-M1-01, FR-M1-05, Multi-Tenancy)
    """
    # 2. Derive unique restaurant slug
    base_slug = re.sub(r"[^a-z0-9]+", "-", restaurant_name.strip().lower()).strip("-")
    if not base_slug:
        base_slug = "restaurant"
    candidate_slug = base_slug
    suffix = 1
    while True:
        existing_slug = await db.execute(select(Restaurant).where(Restaurant.slug == candidate_slug))
        if not existing_slug.scalar_one_or_none():
            break
        suffix += 1
        candidate_slug = f"{base_slug}-{suffix}"

    # 3. Create Restaurant
    clerk_org_id = f"org_{clerk_user_id[-8:]}" if clerk_user_id else None
    restaurant = Restaurant(
        name=restaurant_name.strip(),
        slug=candidate_slug,
        address=address,
        phone=phone,
        currency=currency.upper(),
        clerk_org_id=clerk_org_id,
        is_active=True,
    )
    db.add(restaurant)
    await db.flush()

    # 4. Create Manager User
    manager_user = User(
        restaurant_id=restaurant.id,
        email=email,
        phone_number=phone,
        hashed_password=password_hash,
        clerk_user_id=clerk_user_id,
        role=UserRole.MANAGER,
        is_active=True,
        is_verified=True,
    )
    db.add(manager_user)
    await db.flush()
    profile = UserProfile(
        user_id=manager_user.id,
        display_name=manager_name.strip(),
        preferred_language="en",
        push_notifications_enabled=True,
    )
    db.add(profile)
    await db.flush()

    # 4b. Seed Real Starter Team Profiles for this restaurant
    starter_team = [
        (f"chef.{candidate_slug}@mezflow.com", f"{restaurant_name.strip()} Head Chef", UserRole.KITCHEN_STAFF),
        (f"waiter.{candidate_slug}@mezflow.com", f"{restaurant_name.strip()} Floor Captain", UserRole.SERVICE_STAFF),
        (f"cashier.{candidate_slug}@mezflow.com", f"{restaurant_name.strip()} Cashier Station", UserRole.CASHIER),
    ]
    for s_email, s_name, s_role in starter_team:
        s_user = User(
            restaurant_id=restaurant.id,
            email=s_email,
            hashed_password=get_password_hash(secrets.token_urlsafe(24)),  # manager sets real ones from the console
            role=s_role,
            is_active=True,
            is_verified=True,
        )
        db.add(s_user)
        await db.flush()
        db.add(
            UserProfile(
                user_id=s_user.id,
                display_name=s_name,
                preferred_language="en",
                push_notifications_enabled=True,
            )
        )
    await db.flush()

    # 5. Seed 10 starter dining tables with QR code tokens
    for t_num in range(1, 11):
        db.add(
            Table(
                restaurant_id=restaurant.id,
                table_number=t_num,
                capacity=4,
                status=TableStatus.AVAILABLE,
                qr_code_token=f"QR-{candidate_slug}-T{t_num}-{secrets.token_hex(3).upper()}",
            )
        )

    # 6. Seed starter menu categories and initial dishes
    cat_objs = []
    categories = [
        ("Starters & Appetizers", 1),
        ("Main Course", 2),
        ("Beverages & Drinks", 3),
        ("Desserts", 4),
    ]
    for cat_name, order in categories:
        c_obj = MenuCategory(restaurant_id=restaurant.id, name=cat_name, sort_order=order)
        db.add(c_obj)
        cat_objs.append(c_obj)
    await db.flush()

    # Seed starter dishes
    initial_dishes = [
        {
            "category_id": cat_objs[0].id,
            "name": "Crispy Mozzarella Sticks",
            "name_ur": "کرسپی موزریلا سٹکس",
            "description": "Golden crumbed mozzarella cheese with spicy marinara dipping sauce.",
            "description_ur": "موزریلا پنیر اور مسالہ دار ساس۔",
            "price": 650.00,
            "kitchen_station": "fryer",
            "expected_prep_minutes": 10,
            "dietary_tags": ["vegetarian", "halal"],
            "image_url": "https://images.unsplash.com/photo-1548340748-6d2b7d7da280?auto=format&fit=crop&w=600&q=80",
        },
        {
            "category_id": cat_objs[0].id,
            "name": "Dynamite Buffalo Wings",
            "name_ur": "ڈائنامائٹ بفیلو ونگز",
            "description": "Crispy fried chicken wings tossed in tangy buffalo glaze with ranch.",
            "description_ur": "کرسپی چکن ونگز اور بفیلو ساس۔",
            "price": 850.00,
            "kitchen_station": "fryer",
            "expected_prep_minutes": 12,
            "dietary_tags": ["halal"],
            "image_url": "https://images.unsplash.com/photo-1567620832903-9fc6debc209f?auto=format&fit=crop&w=600&q=80",
        },
        {
            "category_id": cat_objs[1].id,
            "name": "Royal Chicken Karahi",
            "name_ur": "شاہی چکن کڑاہی",
            "description": "Tender chicken cooked with fresh tomatoes, ginger, and roasted spices in a traditional wok.",
            "description_ur": "روایتی کڑاہی میں تیار شدہ تازہ چکن اور مسالے۔",
            "price": 1650.00,
            "kitchen_station": "hot_kitchen",
            "expected_prep_minutes": 20,
            "dietary_tags": ["halal", "spicy"],
            "image_url": "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=600&q=80",
        },
        {
            "category_id": cat_objs[1].id,
            "name": "Gourmet Angus Beef Burger",
            "name_ur": "گورمے بیف برگر",
            "description": "Juicy grilled beef patty with aged cheddar, caramelized onions, and secret sauce on brioche.",
            "description_ur": "گرلڈ بیف پیٹی اور چیڈر پنیر برگر۔",
            "price": 1250.00,
            "kitchen_station": "grill",
            "expected_prep_minutes": 15,
            "dietary_tags": ["halal"],
            "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=600&q=80",
        },
        {
            "category_id": cat_objs[2].id,
            "name": "Fresh Mint Lemonade",
            "name_ur": "تازہ پودینہ لیمونیڈ",
            "description": "Crushed mint leaves, fresh lime juice, black salt, and sparkling soda.",
            "description_ur": "پودینہ، لیموں کا رس اور سوڈا۔",
            "price": 350.00,
            "kitchen_station": "drinks",
            "expected_prep_minutes": 5,
            "dietary_tags": ["vegetarian", "halal"],
            "image_url": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=80",
        },
        {
            "category_id": cat_objs[2].id,
            "name": "Traditional Karak Chai",
            "name_ur": "روایتی کڑک چائے",
            "description": "Slowly brewed black tea leaves with evaporated milk and crushed cardamom.",
            "description_ur": "دودھ پتی کڑک چائے الائچی کے ساتھ۔",
            "price": 180.00,
            "kitchen_station": "drinks",
            "expected_prep_minutes": 6,
            "dietary_tags": ["halal"],
            "image_url": "https://images.unsplash.com/photo-1571934811356-5cc061b6821f?auto=format&fit=crop&w=600&q=80",
        },
        {
            "category_id": cat_objs[3].id,
            "name": "Warm Chocolate Lava Cake",
            "name_ur": "گرم چاکلیٹ لاوا کیک",
            "description": "Decadent dark chocolate molten cake with a scoop of artisanal vanilla ice cream.",
            "description_ur": "گرم چاکلیٹ کیک اور ونیلا آئس کریم۔",
            "price": 750.00,
            "kitchen_station": "dessert",
            "expected_prep_minutes": 10,
            "dietary_tags": ["vegetarian", "halal"],
            "image_url": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=600&q=80",
        },
        {
            "category_id": cat_objs[3].id,
            "name": "Authentic Warm Gulab Jamun",
            "name_ur": "خالص گرم گلاب جامن",
            "description": "Tender milk-solid dumplings soaked in rose and cardamom saffron syrup.",
            "description_ur": "زعفرانی شیرے میں ڈوبے ہوئے گلاب جامن۔",
            "price": 450.00,
            "kitchen_station": "dessert",
            "expected_prep_minutes": 5,
            "dietary_tags": ["vegetarian", "halal"],
            "image_url": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80",
        },
    ]
    for d_item in initial_dishes:
        db.add(MenuItem(restaurant_id=restaurant.id, **d_item))

    # 7. Record immutable audit log
    ip = _get_client_ip(request)
    await record_audit_log(
        db=db,
        restaurant_id=restaurant.id,
        user_id=manager_user.id,
        action="RESTAURANT_REGISTERED",
        resource_type="restaurant",
        resource_id=str(restaurant.id),
        details={"restaurant_name": restaurant.name, "slug": restaurant.slug, "email": email},
        ip_address=ip,
    )

    await db.commit()
    res = await db.execute(select(User).options(selectinload(User.profile)).where(User.id == manager_user.id))
    return res.scalar_one()


SIGNUP_SENT = "We sent a 6-digit verification code to your email."


@router.post(
    "/register-restaurant/start",
    tags=["Authentication", "Multi-Tenancy"],
    summary="Step 1 of sign-up: e-mail a 6-digit code (nothing is created yet)",
)
async def register_restaurant_start(
    data: RestaurantRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Validates the form, remembers it for 15 minutes and e-mails a verification code."""
    email = data.email.strip().lower()
    # EmailStr accepts one-letter endings like "ali@gmail.c"; no such domain exists, so catch the typo here
    if len(email.rsplit(".", 1)[-1]) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is not valid. Please check the part after the dot (e.g. name@gmail.com).")
    if not data.password or len(data.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters long.")
    if await _email_taken(db, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ACCOUNT_EXISTS)

    now = datetime.now(timezone.utc)
    pending = (await db.execute(select(PendingRegistration).where(PendingRegistration.email == email))).scalar_one_or_none()
    if pending and (now - pending.last_sent_at).total_seconds() < settings.SIGNUP_CODE_RESEND_SECONDS:
        wait = settings.SIGNUP_CODE_RESEND_SECONDS - int((now - pending.last_sent_at).total_seconds())
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"A code was just sent. Please wait {wait} seconds before asking again.")

    code = f"{secrets.randbelow(900000) + 100000}"
    payload = {
        "restaurant_name": data.restaurant_name.strip(),
        "manager_name": data.manager_name.strip(),
        "currency": data.currency.upper(),
        "phone": (data.phone or "").strip() or None,
        "address": (data.address or "").strip() or None,
    }
    if not pending:
        pending = PendingRegistration(email=email)
        db.add(pending)
    pending.payload = payload
    pending.password_hash = get_password_hash(data.password)
    pending.code_hash = hash_signup_code(email, code)
    pending.expires_at = now + timedelta(minutes=settings.SIGNUP_CODE_EXPIRE_MINUTES)
    pending.attempts = 0
    pending.last_sent_at = now

    try:
        await notify.send_email(
            email,
            "Your MezFlow verification code",
            f"Welcome to MezFlow!\n\nYour verification code is {code}. It expires in {settings.SIGNUP_CODE_EXPIRE_MINUTES} minutes.\n\n"
            "If you did not try to create a MezFlow account, ignore this e-mail.",
        )
    except notify.NotifyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not send the verification email right now. Please try again shortly.")
    await db.commit()
    return {"success": True, "message": SIGNUP_SENT, "email": email}


@router.post(
    "/register-restaurant/verify",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication", "Multi-Tenancy"],
    summary="Step 2 of sign-up: check the code, create the workspace and log in",
)
async def register_restaurant_verify(
    data: SignupVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    email = data.email.strip().lower()
    bad_code = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This code is wrong or has expired. Please request a new one.")
    now = datetime.now(timezone.utc)
    pending = (await db.execute(select(PendingRegistration).where(PendingRegistration.email == email))).scalar_one_or_none()
    if not pending or pending.expires_at < now or pending.attempts >= settings.SIGNUP_CODE_MAX_ATTEMPTS:
        raise bad_code

    pending.attempts += 1
    if not secrets.compare_digest(pending.code_hash, hash_signup_code(email, data.code)):
        left = settings.SIGNUP_CODE_MAX_ATTEMPTS - pending.attempts
        await db.commit()  # keep the attempt count; get_db rolls back on exceptions
        if left <= 0:
            raise bad_code
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Incorrect code. {left} attempt(s) left.")

    if await _email_taken(db, email):
        await db.delete(pending)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ACCOUNT_EXISTS)

    p = pending.payload
    password_hash = pending.password_hash
    await db.delete(pending)
    manager = await _provision_workspace(
        db,
        request,
        restaurant_name=p["restaurant_name"],
        manager_name=p["manager_name"],
        email=email,
        password_hash=password_hash,
        currency=p.get("currency") or "PKR",
        phone=p.get("phone"),
        address=p.get("address"),
    )
    return _token_response(manager, manager.restaurant_id)


@router.post(
    "/register-restaurant",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication", "Multi-Tenancy"],
    summary="Google (Clerk) sign-up: create or open the workspace for a verified Clerk user",
)
async def register_restaurant(
    data: ClerkRegisterRequest,
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Requires the Clerk session token in the Authorization header; the Clerk user id and e-mail come
    from Clerk itself, never from the request body. E-mail/password sign-ups use /register-restaurant/start.
    """
    claims = verify_clerk_session_token(auth_header.credentials if auth_header else "")
    if not claims or not claims.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google sign-in could not be verified. Please try again.")
    clerk_user_id = str(claims["sub"])

    def _load(*where):
        return select(User).options(selectinload(User.profile)).where(*where)

    # Returning Google user: open their workspace
    user = (await db.execute(_load(User.clerk_user_id == clerk_user_id))).scalar_one_or_none()
    if user:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")
        return _token_response(user, user.restaurant_id)

    email = await fetch_clerk_verified_email(clerk_user_id)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your Google email is not verified. Please try again.")

    # Same e-mail already registered with the form: Google has proven ownership, so link it to that account
    matches = (await db.execute(_load(func.lower(User.email) == email))).scalars().all()
    if len(matches) > 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This email belongs to several restaurants. Please sign in with your password.")
    if matches:
        user = matches[0]
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")
        user.clerk_user_id = clerk_user_id
        await record_audit_log(
            db=db,
            restaurant_id=user.restaurant_id,
            user_id=user.id,
            action="GOOGLE_ACCOUNT_LINKED",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=_get_client_ip(request),
        )
        await db.commit()
        return _token_response(user, user.restaurant_id)

    manager = await _provision_workspace(
        db,
        request,
        restaurant_name=data.restaurant_name or f"{(data.manager_name or 'My').split(' ')[0]}'s Restaurant",
        manager_name=data.manager_name or email.split("@")[0],
        email=email,
        password_hash=get_password_hash(secrets.token_urlsafe(32)),  # Google-only until they set one via Forgot password
        currency=(data.currency or "PKR").upper(),
        phone=data.phone,
        address=data.address,
        clerk_user_id=clerk_user_id,
    )
    return _token_response(manager, manager.restaurant_id)


@router.post(
    "/onboarding",
    tags=["Authentication", "Multi-Tenancy"],
    summary="Update restaurant profile and manager preferences during onboarding",
)
async def update_onboarding(
    data: OnboardingRequest,
    current_user: User = Depends(require_roles([UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Allows a newly registered or Clerk-authenticated Manager to customize
    their restaurant details (name, address, phone, currency) and display name.
    """
    rest_stmt = select(Restaurant).where(Restaurant.id == current_user.restaurant_id)
    restaurant = (await db.execute(rest_stmt)).scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")

    if data.restaurant_name:
        restaurant.name = data.restaurant_name.strip()
    if data.address is not None:
        restaurant.address = data.address.strip()
    if data.phone is not None:
        restaurant.phone = data.phone.strip()
    if data.currency:
        restaurant.currency = data.currency.upper().strip()

    if data.display_name and current_user.profile:
        current_user.profile.display_name = data.display_name.strip()

    await db.commit()
    return {
        "message": "Restaurant onboarding details saved successfully.",
        "restaurant_id": str(restaurant.id),
        "restaurant_name": restaurant.name,
        "currency": restaurant.currency,
    }
