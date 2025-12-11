from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import timedelta

from app.database import get_db
from app.config import settings
from app.utils.security import create_access_token
from app.dependencies import get_current_user  # ADD THIS
from supabase import create_client

router = APIRouter()

# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login user and return JWT token
    For now, we'll use simple email/password check
    Later integrate with Supabase Auth
    """
    # TODO: Implement proper authentication with Supabase
    # This is a placeholder for development
    
    # Query user from database
    from sqlalchemy import text
    result = db.execute(
        text("SELECT id, email, name, role, organization_id, outlet_id FROM users WHERE email = :email"),
        {"email": request.email}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create JWT token with custom claims
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(result.id),
            "email": result.email,
            "role": result.role,
            "organization_id": str(result.organization_id),
            "outlet_id": str(result.outlet_id) if result.outlet_id else None
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(result.id),
            "email": result.email,
            "name": result.name,
            "role": result.role,
            "organization_id": str(result.organization_id)
        }
    }


@router.get("/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return current_user