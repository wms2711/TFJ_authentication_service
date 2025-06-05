"""
Redis Messaging Service
=======================

Handles interaction with Redis for publishing application events to:
1. Redis Pub/Sub channel (for real-time communication)
2. Redis Streams (for persistent job queueing)

Used by:
- ApplicationService (to notify ML processing pipeline)
"""

import redis
import json
from app.config import settings
from utils.logger import init_logger
from typing import Optional
from uuid import UUID
from app.database.models.enums.application import RedisAction

# Configure logger
logger = init_logger("RedisService")

class RedisService:
    """Main redis service handling job application messaging."""

    def __init__(self):
        """
        Initialize Redis connection and configuration.
        
        Uses settings from environment/config file:
        - REDIS_HOST
        - REDIS_PORT
        - REDIS_PASSWORD
        - REDIS_STREAM_KEY
        """
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.stream_key = settings.REDIS_STREAM_KEY
        self.withdraw_stream_key = settings.REDIS_WITHDRAW__STREAM_KEY
        self.pubsub_channel = "ml_requests"

    def publish_application(
            self, 
            application_id: int, 
            user_id: int, 
            job_id: UUID,
            action: RedisAction
        ):
        """
        Publish application event to Redis Pub/Sub and Stream.
        
        Flow:
        1. Publishes JSON message to 'ml_requests' Pub/Sub channel
        2. Adds structured entry to Redis Stream with application status
        
        Args:
            application_id (int): ID of the submitted job application
            user_id (int): ID of the user
            job_id (UUID): ID of the job
        
        Structure:
            {
                "application_id": application_id,
                "user_id": user_id,
                "job_id": job_id,
                "status": "pending"
            }
        """
        try:
            # Convert UUID to str for job_id
            job_id_str = str(job_id)
            message = {
                "application_id": application_id,
                "user_id": user_id,
                "job_id": job_id_str
            }

            # Publish to both Pub/Sub and Streams
            self.client.publish(
                self.pubsub_channel,
                json.dumps(message)
            )
            
            # Check redis action
            if action == RedisAction.APPLY:
                stream_name = self.stream_key
            
            elif action == RedisAction.WITHDRAW:
                stream_name = self.withdraw_stream_key

            else:
                logger.error("No correct actions specified for redis streams to post actions")
                raise RuntimeError("No correct actions specified for redis streams to post actions")
            # Add to durable stream for tracking and history (local storage)
            self.client.xadd(
                name=stream_name,
                fields=message,
                maxlen=10000  # Retain only the latest 10000 records
            )
            logger.info(f"📤 Published application {application_id} to Redis.")

        except redis.RedisError as e:
            logger.exception(f"❌ Redis publish failed: {str(e)}")
            raise RuntimeError("Failed to publish application event to Redis") from e

        # TODO: Stream, to continue store locally? Redis cloud? AWS ElastiCache?

    def is_connected(self) -> bool:
        """
        Healthcheck for Redis.
        """
        try:
            return self.client.ping()
        except redis.RedisError:
            return False
        
    async def get_cache(self, key: str) -> Optional[dict]:
        """Get cached JSON data from Redis."""
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Cache get failed for key {key}: {str(e)}")
            return None
        
    async def set_cache(self, key: str, value: dict, ttl: int = 300) -> bool:
        """Set JSON data in Redis cache with TTL."""
        try:
            return bool(
                self.client.set(
                    key,
                    json.dumps(value),
                    ex=ttl
                )
            )
        except (redis.RedisError, TypeError) as e:
            logger.error(f"Cache set failed for key {key}: {str(e)}")
            return False

    async def invalidate_cache(self, pattern: str) -> None:
        """Delete cache keys matching pattern."""
        try:
            keys = self.client.keys(pattern + "*")
            if keys:
                self.client.delete(*keys)
        except redis.RedisError as e:
            logger.error(f"Cache invalidation failed for pattern {pattern}: {str(e)}")


