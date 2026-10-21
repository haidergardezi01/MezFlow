from typing import List, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

# Reusable HTTP Bearer security scheme
security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extracts and verifies JWT token from Authorization header,
    returning the authenticated User with loaded profile.
    (FR-M1-02, FR-M1-03)
    """
    if not auth_header or not auth_header.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: No token provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload["sub"]
    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token identity.",
        )

    stmt = (
        select(User)
        .options(selectinload(User.profile), selectinload(User.restaurant))
        .where(User.id == user_uuid)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User associated with token no longer exists.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact management.",
        )

    return user


def require_roles(allowed_roles: List[UserRole]):
    """
    Role-Based Access Control (RBAC) dependency factory.
    Enforces server-side permissions for API routes. (FR-M1-03, NFR-07)
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of roles {[r.value for r in allowed_roles]}.",
            )
        return current_user

    return role_checker


def require_manager():
    """Dependency shorthand restricting access to Manager role only."""
    return require_roles([UserRole.MANAGER])


def require_staff():
    """Dependency shorthand for all internal restaurant staff."""
    return require_roles([
        UserRole.MANAGER,
        UserRole.KITCHEN_STAFF,
        UserRole.SERVICE_STAFF,
        UserRole.CASHIER,
    ])


def enforce_tenant(restaurant_id: UUID, current_user: User = Depends(get_current_user)) -> User:
    """
    Enforces that the user belongs strictly to the requested restaurant.
    Guarantees multi-tenant data isolation. (FR-M1-07, NFR-08)
    """
    if current_user.restaurant_id != restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot access data of another restaurant.",
        )
    return current_user
