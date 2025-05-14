from fastapi import Depends
from app.services.redis import RedisService
import asyncio

class MLClient:
    def __init__(self, redis: RedisService = Depends()):
        self.redis = redis

    async def submit_application(self, application_id: int):
        print(f"Mock processing app {application_id}")
        # Simulate processing delay
        await asyncio.sleep(1)
        return True