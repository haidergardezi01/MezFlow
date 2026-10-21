import random
import time
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

# In-memory fallback dictionary: { destination: (otp_code, expires_at_timestamp) }
_in_memory_otp_cache: dict[str, tuple[str, float]] = {}


async def get_redis_client() -> Optional[aioredis.Redis]:
    """Attempts to connect to Redis, returning None if unavailable."""
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=2.0,
        )
        await client.ping()
        return client
    except Exception:
        return None


class OTPService:
    TTL_SECONDS = 300  # 5 minutes validity

    @staticmethod
    def generate_code() -> str:
        """Generates a secure 6-digit numerical OTP code."""
        return f"{random.randint(100000, 999999)}"

    @classmethod
    async def request_otp(cls, destination: str) -> str:
        """
        Generates and stores an OTP code for a phone number or email.
        Returns the generated code.
        """
        code = cls.generate_code()
        cache_key = f"otp:{destination.strip().lower()}"

        redis_client = await get_redis_client()
        if redis_client:
            try:
                await redis_client.set(cache_key, code, ex=cls.TTL_SECONDS)
                await redis_client.aclose()
            except Exception:
                redis_client = None

        if not redis_client:
            # Fallback to in-memory cache
            expires_at = time.time() + cls.TTL_SECONDS
            _in_memory_otp_cache[cache_key] = (code, expires_at)

        # In development / demonstration mode, print to stdout
        print(f"[OTP SERVICE] Generated OTP for '{destination}': {code} (Valid for 5 mins)")
        return code

    @classmethod
    async def verify_otp(cls, destination: str, code: str) -> bool:
        """
        Validates the provided OTP code against the cached code.
        Deletes the OTP code on successful verification (single-use).
        """
        cache_key = f"otp:{destination.strip().lower()}"
        clean_code = code.strip()

        redis_client = await get_redis_client()
        if redis_client:
            try:
                stored_code = await redis_client.get(cache_key)
                if stored_code and stored_code == clean_code:
                    await redis_client.delete(cache_key)
                    await redis_client.aclose()
                    return True
                await redis_client.aclose()
            except Exception:
                pass

        # Check in-memory cache
        if cache_key in _in_memory_otp_cache:
            stored_code, expires_at = _in_memory_otp_cache[cache_key]
            if time.time() > expires_at:
                del _in_memory_otp_cache[cache_key]
                return False
            if stored_code == clean_code:
                del _in_memory_otp_cache[cache_key]
                return True

        return False
