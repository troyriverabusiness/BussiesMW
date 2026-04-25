import os
from functools import lru_cache

from supabase import Client, create_client


class SupabaseConfigurationError(RuntimeError):
    """Raised when required server-side Supabase credentials are missing."""


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Create the server-side Supabase client used by request handlers."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise SupabaseConfigurationError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured for the server."
        )

    return create_client(supabase_url, supabase_key)
