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
        self.pubsub_channel = "ml_requests"

    def publish_application(self, application_id: int, user_id: int, job_id: str):
        """
        Publish application event to Redis Pub/Sub and Stream.
        
        Flow:
        1. Publishes JSON message to 'ml_requests' Pub/Sub channel
        2. Adds structured entry to Redis Stream with application status
        
        Args:
            application_id (int): ID of the submitted job application
            user_id (int): ID of the user
            job_id (str): ID of the job
        
        Structure:
            {
                "application_id": application_id,
                "user_id": user_id,
                "job_id": job_id,
                "status": "pending"
            }
        """
        # Publish to both Pub/Sub and Streams
        self.client.publish(
            self.pubsub_channel,
            json.dumps({"application_id": application_id})
        )

        # Add to durable stream for tracking and history
        self.client.xadd(
            name=self.stream_key,
            fields={
                "application_id": application_id,
                "user_id": user_id,
                "job_id": job_id,
                "status": "pending"
            },
            maxlen=10000  # Retain only the latest 10000 records
        )