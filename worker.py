import json
import redis
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
    while True:
        messages = r.xread(
            streams={settings.REDIS_STREAM_KEY: last_id},
            count=10,
            block=5000
        )
        
        if not messages:
            continue
            
        for stream_id, message in messages[0][1]:
            try:
                app_id = int(message["application_id"])
                ml.submit_application(app_id)
                r.xack(settings.REDIS_STREAM_KEY, "ml_worker", stream_id)
                last_id = stream_id
            except Exception as e:
                print(f"Failed to process {stream_id}: {str(e)}")

if __name__ == "__main__":
    process_stream()