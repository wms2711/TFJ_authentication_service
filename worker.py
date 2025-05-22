"""
Redis Stream Worker Implementation
=================================

Processes job applications from Redis streams with:
1. Synchronous Redis operations
2. Async ML service integration
3. Retry and dead-letter queue handling
4. Database status tracking
"""

import json
import time
import redis
import asyncio
from app.config import settings
from app.database.session import SessionLocal
from app.services.ml_client import MLClient
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class RedisWorker:
    def __init__(self):
        """
        Initialize worker with:
        - ML client (async capable)
        - Redis connection (sync)
        - Dedicated event loop for async/sync bridging
        """
        self.ml = MLClient()   # Async ML processor
        self.redis = None   # Will hold sync Redis connection
        self.max_retries = 3   # Max retries before DLQ
        self.loop = asyncio.new_event_loop()  # Dedicated async loop
        logger.info("🛠️ Initializing Redis worker...")

    def connect_redis(self):
        """Establish synchronous Redis connection with health check"""
        logger.info(f"🔗 Connecting to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        try:
            self.redis.ping()   # Connection test
            logger.info("✅ Redis connection established")
        except redis.ConnectionError as e:
            logger.error(f"❌ Failed to connect to Redis: {str(e)}")
            raise

    def process_message(self, stream_id, message):
        """
        Process single message from Redis stream
        Args:
            stream_id: Redis stream entry ID 
            message: Decoded message content
        Returns:
            bool: True if processed successfully
        """
        logger.info(f"\n📨 Processing message ID: {stream_id}")
        logger.info(f"📝 Raw message: {message}")

        try:
            app_id = int(message["application_id"])
            logger.info(f"🔄 Submitting application ID: {app_id} to ML service")

            try:
                # Bridge async ML call into sync context
                success = self.loop.run_until_complete(asyncio.wait_for(
                    self.ml.submit_application(app_id),
                    timeout=10
                ))
            except asyncio.TimeoutError:
                logger.error("ML request timeout")
                return False
            
            # Database session management (sync, to be changed to async)
            db = SessionLocal()
            try:
                if success:
                    self.redis.xack(settings.REDIS_STREAM_KEY, "ml_worker", stream_id)
                    logger.info(f"✔ Successfully processed message ID: {stream_id}")
                    return True
                else:
                    logger.warning(f"⚠️ ML service returned failure for message ID: {stream_id}")
                    return False
            finally:
                db.close()

        except Exception as e:
            logger.exception(f"❌ Error processing message ID {stream_id}: {str(e)}")
            return False

    def handle_failure(self, message, stream_id, error):
        """
        Handle failed message processing with:
        - Retry logic (up to max_retries)
        - Dead letter queue for permanent failures
        """
        retries = int(message.get("retries", 0))
        if retries < self.max_retries:
            new_retry = retries + 1
            logger.info(f"♻️ Retrying message (attempt {new_retry}/{self.max_retries})")
            self.redis.xadd(
                settings.REDIS_STREAM_KEY,
                {**message, "retries": new_retry}
            )
        else:
            logger.info(f"☠️ Moving message to DLQ after {self.max_retries} retries")
            self.redis.xadd(
                settings.REDIS_DEAD_STREAM_KEY,
                {**message, "final_error": str(error)}
            )

    def run(self):
        """Main processing loop"""
        self.connect_redis()
        last_id = "$"   # Start from newest message
        logger.info(f"👂 Listening to Redis stream: {settings.REDIS_STREAM_KEY}")

        while True:
            try:
                messages = self.redis.xread(
                    streams={settings.REDIS_STREAM_KEY: last_id},
                    count=10,
                    block=5000   # 5s timeout
                )

                if not messages:
                    logger.info("⏳ No new messages. Waiting...")
                    time.sleep(1)
                    continue

                logger.info(f"📦 Received {len(messages[0][1])} message(s)")
                
                # Process each message in batch
                for stream_id, message in messages[0][1]:
                    success = self.process_message(stream_id, message)
                    if not success:
                        self.handle_failure(message, stream_id, "Processing failed")
                    
                    last_id = stream_id   # Track progress

            except redis.ConnectionError as e:
                logger.error(f"🔌 Redis connection error: {str(e)}. Reconnecting in 5s...")
                time.sleep(5)
                self.connect_redis()
            except Exception as e:
                logger.exception(f"💥 Critical error in stream processing: {str(e)}")
                time.sleep(5)   # Backoff before retry

    def __del__(self):
        """Cleanup event loop on shutdown"""
        if self.redis:
            self.redis.close()
        self.loop.close()

if __name__ == "__main__":
    logger.info("🚀 Starting ML worker service...")
    worker = RedisWorker()
    try:
        worker.run()
    except KeyboardInterrupt:
        logger.warning("\n🛑 Gracefully shutting down worker...")
    except Exception as e:
        logger.exception(f"💣 Fatal error: {str(e)}")