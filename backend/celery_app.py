"""Celery application configuration with enhanced retry policies and monitoring."""

import logging
from celery import Celery
from celery.signals import task_failure, task_retry, task_success
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "mypoolr_circles",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["tasks.rotation", "tasks.reminders", "tasks.defaults", "scheduler", "monitoring"]
)

# Enhanced Celery configuration with retry policies
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task tracking and reliability
    task_track_started=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Retry policies with exponential backoff
    task_default_retry_delay=60,  # 1 minute base delay
    task_max_retries=5,
    task_retry_jitter=True,  # Add randomness to retry delays
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Worker settings
    worker_max_tasks_per_child=1000,  # Restart workers after 1000 tasks
    worker_disable_rate_limits=False,
    
    # Task execution settings
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    
    # Monitoring and logging
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Error handling
    task_ignore_result=False,
    task_store_errors_even_if_ignored=True,
)

# Task routing with priority queues
celery_app.conf.task_routes = {
    "tasks.rotation.*": {"queue": "rotation", "priority": 8},
    "tasks.reminders.*": {"queue": "reminders", "priority": 5},
    "tasks.defaults.*": {"queue": "defaults", "priority": 9},  # Highest priority for defaults
}

# Queue configuration with different priorities
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_queues = {
    "rotation": {"routing_key": "rotation", "priority": 8},
    "reminders": {"routing_key": "reminders", "priority": 5},
    "defaults": {"routing_key": "defaults", "priority": 9},
    "default": {"routing_key": "default", "priority": 1},
}

# Exponential backoff retry decorator
def exponential_backoff_retry(max_retries=5, base_delay=60):
    """Decorator for exponential backoff retry policy."""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                if self.request.retries < max_retries:
                    # Calculate exponential backoff delay
                    delay = base_delay * (2 ** self.request.retries)
                    # Add jitter (random factor between 0.5 and 1.5)
                    import random
                    jitter = random.uniform(0.5, 1.5)
                    final_delay = int(delay * jitter)
                    
                    logger.warning(
                        f"Task {self.name} failed (attempt {self.request.retries + 1}/{max_retries}). "
                        f"Retrying in {final_delay} seconds. Error: {exc}"
                    )
                    raise self.retry(exc=exc, countdown=final_delay)
                else:
                    logger.error(
                        f"Task {self.name} failed permanently after {max_retries} attempts. "
                        f"Final error: {exc}"
                    )
                    raise exc
        return wrapper
    return decorator


# Task monitoring signals
@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """Handle task failures with logging and alerting."""
    logger.error(
        f"Task {sender.name} [{task_id}] failed: {exception}\n"
        f"Traceback: {traceback}"
    )
    # In production, this would send alerts to monitoring systems


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwargs):
    """Handle task retries with logging."""
    logger.warning(
        f"Task {sender.name} [{task_id}] retrying: {reason}"
    )


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Handle successful task completion."""
    logger.info(f"Task {sender.name} completed successfully")


# Health check task for monitoring
@celery_app.task(name="health_check")
def health_check():
    """Simple health check task for monitoring worker status."""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}