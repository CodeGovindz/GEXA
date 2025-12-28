"""
Supabase authentication service for user management.
"""

from typing import Optional
from supabase import create_client, Client
from gotrue.types import AuthResponse, User

from gexa.config import settings


class SupabaseAuth:
    """Supabase authentication service."""
    
    _client: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client."""
        if cls._client is None:
            if not settings.supabase_url or not settings.supabase_anon_key:
                raise ValueError("Supabase URL and Anon Key must be configured")
            cls._client = create_client(
                settings.supabase_url,
                settings.supabase_anon_key
            )
        return cls._client
    
    @classmethod
    async def sign_up(cls, email: str, password: str) -> AuthResponse:
        """Register a new user."""
        client = cls.get_client()
        response = client.auth.sign_up({
            "email": email,
            "password": password
        })
        return response
    
    @classmethod
    async def sign_in(cls, email: str, password: str) -> AuthResponse:
        """Sign in an existing user."""
        client = cls.get_client()
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response
    
    @classmethod
    async def sign_out(cls, access_token: str) -> None:
        """Sign out a user."""
        client = cls.get_client()
        client.auth.sign_out()
    
    @classmethod
    async def get_user(cls, access_token: str) -> Optional[User]:
        """Get user from access token."""
        try:
            client = cls.get_client()
            response = client.auth.get_user(access_token)
            return response.user
        except Exception:
            return None
    
    @classmethod
    async def refresh_token(cls, refresh_token: str) -> AuthResponse:
        """Refresh an access token."""
        client = cls.get_client()
        response = client.auth.refresh_session(refresh_token)
        return response


# Global instance
supabase_auth = SupabaseAuth()
