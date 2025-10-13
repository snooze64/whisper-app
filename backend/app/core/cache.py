"""
Redis cache utilities
"""
import json
import redis
from typing import Any, Optional
from app.core.config import settings


# Redis client instance
redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    global redis_client

    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )

    return redis_client


def get_cached_data(key: str) -> Optional[Any]:
    """
    Get cached data from Redis

    Args:
        key: Cache key

    Returns:
        Cached data or None if not found
    """
    try:
        client = get_redis_client()
        data = client.get(key)
        if data:
            return json.loads(data)
        return None
    except (redis.RedisError, json.JSONDecodeError):
        # If Redis is unavailable or data is corrupted, return None
        return None


def set_cached_data(key: str, data: Any, ttl: int = 30) -> bool:
    """
    Set cached data in Redis

    Args:
        key: Cache key
        data: Data to cache (will be JSON serialized)
        ttl: Time-to-live in seconds (default: 30 seconds)

    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        serialized_data = json.dumps(data)
        client.setex(key, ttl, serialized_data)
        return True
    except (redis.RedisError, TypeError, json.JSONEncodeError):
        # If Redis is unavailable or data cannot be serialized, return False
        return False


def delete_cached_data(key: str) -> bool:
    """
    Delete cached data from Redis

    Args:
        key: Cache key

    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        client.delete(key)
        return True
    except redis.RedisError:
        return False


def delete_pattern(pattern: str) -> bool:
    """
    Delete all keys matching a pattern

    Args:
        pattern: Pattern to match (e.g., "dashboard:*")

    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
        return True
    except redis.RedisError:
        return False
