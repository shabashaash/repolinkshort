from celery import Celery
import os

celery_app = Celery(
    "shortener",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1"),
    backend=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1"),
    include=["tasks.cleanup"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "cleanup-expired-every-hour": {
            "task": "tasks.cleanup.cleanup_expired_links",
            "schedule": 3600.0,
        },
        "cleanup-unused-daily": {
            "task": "tasks.cleanup.cleanup_unused_links",
            "schedule": 86400.0,
        },
    },
)