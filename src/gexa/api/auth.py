"""
API Key authentication and authorization.
"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.config import settings
from gexa.database import get_async_db, ApiKey


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_header = APIKeyHeader(name="Authorization", auto_error=False)


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    salted = f"{settings.api_key_salt}{key}"
    return hashlib.sha256(salted.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key and its hash.
    
    Returns:
        Tuple of (plain_key, key_hash)
    """
    # Generate a secure random key
    key = f"gx_{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(key)
    return key, key_hash


def get_key_prefix(key: str) -> str:
    """Get the prefix of an API key for identification."""
    return key[:8]


async def get_api_key(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[str] = Security(bearer_header),
    db: AsyncSession = Depends(get_async_db),
) -> ApiKey:
    """Validate and return the API key from the request.
    
    Supports both X-API-Key header and Bearer authorization.
    """
    # Try to get key from either header
    key = api_key
    if not key and bearer:
        if bearer.lower().startswith("bearer "):
            key = bearer[7:]
        else:
            key = bearer
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required. Provide via X-API-Key header or Authorization: Bearer <key>",
        )
    
    # Hash the key and look it up
    key_hash = hash_api_key(key)
    
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    )
    api_key_record = result.scalar_one_or_none()
    
    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    if not api_key_record.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is inactive",
        )
    
    if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key has expired",
        )
    
    # Check quota
    if api_key_record.quota_used >= api_key_record.quota_total:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API quota exceeded",
        )
    
    # Update last used timestamp
    api_key_record.last_used_at = datetime.utcnow()
    await db.commit()
    
    return api_key_record


async def increment_quota(api_key: ApiKey, db: AsyncSession, amount: int = 1):
    """Increment the quota used for an API key."""
    api_key.quota_used += amount
    await db.commit()
