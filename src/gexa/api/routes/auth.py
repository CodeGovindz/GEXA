"""
User authentication routes for signup, login, and logout.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.api.auth_supabase import supabase_auth
from gexa.database import get_async_db, ApiKey
from gexa.api.auth import generate_api_key, get_key_prefix


router = APIRouter()


# Request/Response Models
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    message: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    api_key: Optional[str] = None  # First-time API key for new users


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    user_id: str
    email: str


@router.post("/signup", response_model=AuthResponse)
async def signup(
    request: SignUpRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Register a new user account.
    
    Creates a user in Supabase Auth and automatically generates
    their first API key for accessing the GEXA API.
    """
    try:
        response = await supabase_auth.sign_up(request.email, request.password)
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user. Email may already be registered."
            )
        
        user_id = response.user.id
        
        # Create first API key for the new user
        key, key_hash = generate_api_key()
        key_prefix = get_key_prefix(key)
        
        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Default Key",
            owner_email=request.email,
            user_id=user_id,
            quota_total=1000,  # Default quota for new users
        )
        
        db.add(api_key)
        await db.commit()
        
        return AuthResponse(
            message="Account created successfully! Please check your email to verify.",
            user_id=user_id,
            email=request.email,
            access_token=response.session.access_token if response.session else None,
            refresh_token=response.session.refresh_token if response.session else None,
            expires_in=response.session.expires_in if response.session else None,
            api_key=key  # Only shown once!
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.
    
    Returns access and refresh tokens for authenticated requests.
    """
    try:
        response = await supabase_auth.sign_in(request.email, request.password)
        
        if response.user is None or response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        return AuthResponse(
            message="Login successful",
            user_id=response.user.id,
            email=response.user.email,
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )


@router.post("/logout")
async def logout():
    """
    Logout the current user.
    
    Invalidates the current session on the client side.
    """
    try:
        await supabase_auth.sign_out("")
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh an access token using a refresh token.
    """
    try:
        response = await supabase_auth.refresh_token(request.refresh_token)
        
        if response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return AuthResponse(
            message="Token refreshed",
            user_id=response.user.id if response.user else None,
            email=response.user.email if response.user else None,
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(access_token: str):
    """
    Get current user information from access token.
    """
    user = await supabase_auth.get_user(access_token)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return UserResponse(
        user_id=user.id,
        email=user.email
    )
