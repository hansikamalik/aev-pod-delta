import os
import time
import redis
from fastapi import HTTPException

# Connect to Redis with 1 sec timeout
redis_client = redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    socket_timeout=1.0,
    socket_connect_timeout=1.0
)

# Token bucket settings
BUCKET_CAPACITY = 8        # Max tokens a user can save up (allows a burst)
REFILL_RATE = 5 / 60       # Tokens added per second (5 per 60s, same long-term average as before)

# Lua script: read bucket state, refill it based on elapsed time, try to
# spend 1 token. Runs atomically in Redis so concurrent requests can't
# race each other.
_TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local bucket = redis.call("HMGET", key, "tokens", "last_refill")
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
    tokens = capacity
    last_refill = now
end

local elapsed = now - last_refill
tokens = math.min(capacity, tokens + elapsed * refill_rate)

local allowed = 0
if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
end

redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
redis.call("EXPIRE", key, 3600)

return {allowed, tokens}
"""
_token_bucket = redis_client.register_script(_TOKEN_BUCKET_SCRIPT)


def check_rate_limit(user_id: str):
    """
    Check if a user has exceeded their rate limit, using a token-bucket
    algorithm so a short burst of requests is allowed instead of an
    instant hard block, while the long-term average rate stays the same.
    Includes graceful degradation if Redis is offline locally.
    """
    key = f"rate_limit:{user_id}"
    now = time.time()

    try:
        allowed, tokens_remaining = _token_bucket(
            keys=[key],
            args=[BUCKET_CAPACITY, REFILL_RATE, now],
        )

        if not allowed:
            retry_after = round((1 - tokens_remaining) / REFILL_RATE)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": "You're sending requests too quickly. "
                               f"Try again in {retry_after} seconds.",
                    "retry_after_seconds": retry_after,
                }
            )

        return {
            "allowed": True,
            "tokens_remaining": round(tokens_remaining, 2),
            "bucket_capacity": BUCKET_CAPACITY,
        }
    except (
        redis.exceptions.ConnectionError,
        redis.exceptions.TimeoutError,
        redis.exceptions.RedisError
    ):
        # Graceful fallback when running locally without active Redis daemon
        return {
            "allowed": True,
            "tokens_remaining": BUCKET_CAPACITY - 1,
            "bucket_capacity": BUCKET_CAPACITY,
            "warning": "Redis unavailable"
        }
