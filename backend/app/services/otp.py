import secrets
import time
from typing import Optional, Tuple
import redis.asyncio as aioredis
from app.core.config import settings

# In-memory fallback dictionary: { destination: {"code": otp_code, "expires_at": timestamp, "attempts": int} }
_in_memory_otp_cache: dict[str, dict] = {}


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
    MAX_ATTEMPTS = 5   # Max allowed failed attempts before invalidation

    @staticmethod
    def generate_code() -> str:
        """Generates a cryptographically secure 6-digit numerical OTP code using secrets."""
        return f"{secrets.randbelow(900000) + 100000}"

    @classmethod
    async def request_otp(cls, destination: str) -> str:
        """
        Generates and stores a cryptographically secure OTP code for a phone number or email.
        Resets attempt counter and sets 5-minute expiry.
        """
        code = cls.generate_code()
        cache_key = f"otp:{destination.strip().lower()}"
        attempts_key = f"otp_attempts:{destination.strip().lower()}"

        redis_client = await get_redis_client()
        if redis_client:
            try:
                await redis_client.set(cache_key, code, ex=cls.TTL_SECONDS)
                await redis_client.set(attempts_key, "0", ex=cls.TTL_SECONDS)
                await redis_client.aclose()
            except Exception:
                redis_client = None

        if not redis_client:
            # Fallback to in-memory cache
            expires_at = time.time() + cls.TTL_SECONDS
            _in_memory_otp_cache[cache_key] = {
                "code": code,
                "expires_at": expires_at,
                "attempts": 0,
            }

        # In development / demonstration mode, log to stdout
        if settings.ENVIRONMENT == "development":
            print(f"[OTP SERVICE] Generated OTP for '{destination}': {code} (Valid for 5 mins)")
        return code

    @classmethod
    async def verify_otp(cls, destination: str, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validates the provided OTP code against the cached code.
        Enforces a maximum of 5 failed attempts before permanently invalidating the code.
        Returns (is_valid, error_message).
        """
        cache_key = f"otp:{destination.strip().lower()}"
        attempts_key = f"otp_attempts:{destination.strip().lower()}"
        clean_code = code.strip()

        redis_client = await get_redis_client()
        if redis_client:
            try:
                stored_code = await redis_client.get(cache_key)
                if not stored_code:
                    await redis_client.aclose()
                    return False, "OTP has expired or does not exist."

                # Increment attempts
                attempts = await redis_client.incr(attempts_key)
                if attempts > cls.MAX_ATTEMPTS:
                    await redis_client.delete(cache_key)
                    await redis_client.delete(attempts_key)
                    await redis_client.aclose()
                    return False, "Too many failed attempts. This OTP has been invalidated for security."

                if stored_code == clean_code:
                    # Valid code: clear cache and return success
                    await redis_client.delete(cache_key)
                    await redis_client.delete(attempts_key)
                    await redis_client.aclose()
                    return True, None

                remaining = cls.MAX_ATTEMPTS - attempts
                await redis_client.aclose()
                return False, f"Invalid OTP code. {remaining} attempt(s) remaining."
            except Exception:
                pass

        # Check in-memory cache
        if cache_key in _in_memory_otp_cache:
            entry = _in_memory_otp_cache[cache_key]
            if time.time() > entry["expires_at"]:
                del _in_memory_otp_cache[cache_key]
                return False, "OTP has expired or does not exist."

            entry["attempts"] += 1
            if entry["attempts"] > cls.MAX_ATTEMPTS:
                del _in_memory_otp_cache[cache_key]
                return False, "Too many failed attempts. This OTP has been invalidated for security."

            if entry["code"] == clean_code:
                del _in_memory_otp_cache[cache_key]
                return True, None

            remaining = cls.MAX_ATTEMPTS - entry["attempts"]
            return False, f"Invalid OTP code. {remaining} attempt(s) remaining."

        return False, "OTP has expired or does not exist."
