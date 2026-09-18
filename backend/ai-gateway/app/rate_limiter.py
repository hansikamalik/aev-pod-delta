import os
import redis
from fastapi import HTTPException

# Connect to Redis with 1 sec timeout
redis_client = redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    socket_timeout=1.0,
    socket_connect_timeout=1.0
)

# Rate limit settings
RATE_LIMIT = 5             # Max requests allowed (5 per minute)
WINDOW_SECONDS = 60        # Time window in seconds (1 minute)


def check_rate_limit(user_id: str):
    """
    Check if a user has exceeded their rate limit.
    Includes graceful degradation if Redis is offline locally.
    """
    key = f"rate_limit:{user_id}"       # Unique Redis key per user

    try:
        current_count = redis_client.incr(key)
        if current_count == 1:
            redis_client.expire(key, WINDOW_SECONDS)

        ttl = redis_client.ttl(key)

        if current_count > RATE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"You have made {current_count} requests. "
                               f"Limit is {RATE_LIMIT} per {WINDOW_SECONDS} seconds.",
                    "retry_after_seconds": ttl
                }
            )

        return {
            "requests_made": current_count,
            "requests_remaining": RATE_LIMIT - current_count,
            "resets_in_seconds": ttl
        }
    except (
        redis.exceptions.ConnectionError,
        redis.exceptions.TimeoutError,
        redis.exceptions.RedisError
    ):
        # Graceful fallback when running locally without active Redis daemon
        return {
            "requests_made": 1,
            "requests_remaining": RATE_LIMIT - 1,
            "resets_in_seconds": WINDOW_SECONDS,
            "warning": "Redis unavailable"
        }
