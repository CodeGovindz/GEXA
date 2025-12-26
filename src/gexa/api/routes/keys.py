"""
API Keys management endpoint.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.database import get_async_db, ApiKey
from gexa.database.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyInfo
from gexa.api.auth import generate_api_key, get_key_prefix, hash_api_key


router = APIRouter()


@router.post("", response_model=ApiKeyResponse)
async def create_api_key(
    request: ApiKeyCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new API key.
    
    Note: The full API key is only shown once in the response.
    Store it securely as it cannot be retrieved later.
    """
    try:
        # Generate new key
        key, key_hash = generate_api_key()
        key_prefix = get_key_prefix(key)
        
        # Create database record
        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=request.name,
            owner_email=request.owner_email,
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[ApiKeyInfo])
async def list_api_keys(
    db: AsyncSession = Depends(get_async_db),
):
    """List all active API keys (without the actual key values)."""
    try:
        result = await db.execute(
            select(ApiKey).where(ApiKey.is_active == True).order_by(ApiKey.created_at.desc())
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Delete an API key."""
    try:
        result = await db.execute(
            select(ApiKey).where(ApiKey.id == key_id)
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")
        
        # Actually delete the key from the database
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
    db: AsyncSession = Depends(get_async_db),
):
    """Reset the quota for an API key."""
    try:
        result = await db.execute(
            select(ApiKey).where(ApiKey.id == key_id)
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")
        
        api_key.quota_used = 0
        await db.commit()
        
        return {"message": "Quota reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
