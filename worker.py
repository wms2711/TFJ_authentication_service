import json
import redis
import asyncio
from app.config import settings
from app.database.session import SessionLocal
from app.services.ml_client import MLClient

db = SessionLocal()
ml = MLClient()

r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD
)

def process_stream():
    last_id = "$"  # Start from newest message
    print(f"Listening to Redis stream: {settings.REDIS_STREAM_KEY}")
    while True:
        try:
            messages = r.xread(
                streams={settings.REDIS_STREAM_KEY: last_id},
                count=10,
                block=5000  # block for 5 seconds
            )

            if not messages:
                print("No new messages. Waiting...")
                continue

            print(f"Received {len(messages[0][1])} message(s)")
            
            for stream_id, message in messages[0][1]:
                try:
                    print(f"\nProcessing message ID: {stream_id}")
                    print(f"Raw message (bytes): {message}")

                    # Decode bytes to strings
                    decoded_msg = {k.decode(): v.decode() for k, v in message.items()}
                    print(f"Decoded message: {decoded_msg}")

                    app_id = int(decoded_msg["application_id"])
                    print(f"Submitting application ID: {app_id} to ML service")
                    
                    # Run async function submit_application
                    asyncio.run(ml.submit_application(app_id))
                    r.xack(settings.REDIS_STREAM_KEY, "ml_worker", stream_id)

                    print(f"✔ Successfully processed and acknowledged message ID: {stream_id}")
                    last_id = stream_id
                except Exception as e:
                    print(f"❌ Failed to process message ID {stream_id}: {str(e)}")


        except Exception as e:
            print(f"💥 Error in Redis stream reading loop: {str(e)}")

if __name__ == "__main__":
    print("🔁 Starting ML worker to process Redis stream...")
    process_stream()
