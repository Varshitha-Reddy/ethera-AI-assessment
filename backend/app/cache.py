"""
Redis cache utility for caching frequently accessed data.
Reduces database load and improves response times.
"""
import redis.asyncio as redis
from typing import Any, Optional
import json
import logging
from .config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """Async Redis cache manager."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = settings.enable_redis_cache
    
    async def connect(self):
        """Connect to Redis."""
        if not self.enabled:
            logger.info("Cache is disabled")
            return
        
        try:
            self.redis_client = await redis.from_url(settings.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.enabled = False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL (default 1 hour)."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            await self.redis_client.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete value from cache."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
    
    async def clear_pattern(self, pattern: str):
        """Delete all keys matching pattern."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            async for key in self.redis_client.scan_iter(match=pattern, count=250):
                await self.redis_client.unlink(key)
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")

# Global cache manager instance
cache_manager = CacheManager()
