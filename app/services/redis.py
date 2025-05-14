import redis
import json
from app.config import settings

class RedisService:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.stream_key = settings.REDIS_STREAM_KEY
        self.pubsub_channel = "ml_requests"

    def publish_application(self, application_id: int):
        # Publish to both Pub/Sub and Streams
        self.client.publish(
            self.pubsub_channel,
            json.dumps({"application_id": application_id})
        )
        self.client.xadd(
            name=self.stream_key,
            fields={
                "application_id": application_id,
                "status": "pending"
            },
            maxlen=10000  # Keep last 10K jobs
        )