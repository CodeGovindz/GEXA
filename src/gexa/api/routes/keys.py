"""
API Keys management endpoint with user authentication.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.database import get_async_db, ApiKey
from gexa.database.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyInfo
from gexa.api.auth import generate_api_key, get_key_prefix, hash_api_key
from gexa.api.auth_supabase import supabase_auth


router = APIRouter()


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract and validate the current user from the Authorization header.
    Returns the user_id if valid, raises HTTPException otherwise.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required. Please login first."
        )
    
    # Extract token from "Bearer <token>" format
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    # Validate token and get user
    user = await supabase_auth.get_user(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token. Please login again."
        )
    
    return user.id


@router.post("", response_model=ApiKeyResponse)
async def create_api_key(
    request: ApiKeyCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new API key for the authenticated user.
    
    Note: The full API key is only shown once in the response.
    Store it securely as it cannot be retrieved later.
    """
    try:
        # Generate new key
        key, key_hash = generate_api_key()
        key_prefix = get_key_prefix(key)
        
        # Create database record with user_id
        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=request.name,
            owner_email=request.owner_email,
            user_id=user_id,  # Associate with authenticated user
            quota_total=request.quota_total,
            rate_limit_per_minute=request.rate_limit_per_minute,
        )
        
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        
        return ApiKeyResponse(
            id=str(api_key.id),
            key=key,  # Only time we return the full key
            key_prefix=key_prefix,
            name=api_key.name,
            quota_total=api_key.quota_total,
            quota_used=api_key.quota_used,
            rate_limit_per_minute=api_key.rate_limit_per_minute,
            created_at=api_key.created_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[ApiKeyInfo])
async def list_api_keys(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List API keys for the authenticated user only."""
    try:
        # Filter by user_id to only show user's own keys
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.is_active == True)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        keys = result.scalars().all()
        
        return [
            ApiKeyInfo(
                id=str(key.id),
                key_prefix=key.key_prefix,
                name=key.name,
                quota_total=key.quota_total,
                quota_used=key.quota_used,
                rate_limit_per_minute=key.rate_limit_per_minute,
                is_active=key.is_active,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
            )
            for key in keys
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete an API key. Users can only delete their own keys."""
    try:
        # Find key and verify ownership
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.id == key_id)
            .where(ApiKey.user_id == user_id)
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=404, 
                detail="API key not found or you don't have permission to delete it"
            )
        
        # Delete the key
        await db.delete(api_key)
        await db.commit()
        
        return {"message": "API key deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{key_id}/reset-quota")
async def reset_quota(
    key_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Reset the quota for an API key. Users can only reset their own keys."""
    try:
        # Find key and verify ownership
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.id == key_id)
            .where(ApiKey.user_id == user_id)
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=404, 
                detail="API key not found or you don't have permission to reset it"
            )
        
        api_key.quota_used = 0
        await db.commit()
        
        return {"message": "Quota reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
