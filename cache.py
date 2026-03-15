import redis.asyncio as redis
from config import settings
from typing import Optional
import json

class CacheService:
    def __init__(self, url):
        self.redis = redis.from_url(url)
    
    async def get(self, key):
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def set(self, key, value, expire = 300):
        await self.redis.set(key, json.dumps(value), ex=expire)
    
    async def delete(self, key):
        await self.redis.delete(key)
    
    async def delete_pattern(self, pattern):
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await self.redis.delete(*keys)
    
    async def get_stats(self, short_code):
        return await self.get(f"link:stats:{short_code}")
    
    async def set_stats(self, short_code, stats):
        await self.set(f"link:stats:{short_code}", stats, expire=60)
    
    async def invalidate_link(self, short_code):
        await self.delete(f"link:stats:{short_code}")
        await self.delete(f"link:{short_code}")
        await self.delete_pattern(f"link:search:*")

cache = CacheService(settings.REDIS_URL)