from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # FIX: Ganti HTTPAuthCredentials jadi HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.utils.security import decode_access_token

# Security scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # FIX: Ganti type hint
    db: Session = Depends(get_db)
) -> dict:
    """
    Get current authenticated user from JWT token
    Returns user data with organization_id and role
    """
    token = credentials.credentials
    
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    organization_id: str = payload.get("organization_id")
    role: str = payload.get("role")
    
    if user_id is None or organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    return {
        "user_id": user_id,
        "organization_id": organization_id,
        "role": role,
        "email": payload.get("email"),
        "outlet_id": payload.get("outlet_id")
    }


def require_role(*allowed_roles: str):
    """
    Dependency to check if user has required role
    Usage: Depends(require_role("OWNER", "ADMIN"))
    """
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def get_organization_context(
    current_user: dict = Depends(get_current_user)
) -> UUID:
    """
    Get organization_id from current user
    Useful for filtering queries by organization
    """
    return UUID(current_user["organization_id"])