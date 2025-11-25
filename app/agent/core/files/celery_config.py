# celery_config.py
from celery import Celery
from app.config.settings import _settings

# Celery instance
celery_app = Celery(
    _settings.celery.app_name,
    include=_settings.celery.include
)

celery_app.conf.update(
    broker_url=_settings.celery.broker_url,
    result_backend=_settings.celery.result_backend,
    task_serializer=_settings.celery.task_serializer,
    accept_content=_settings.celery.accept_content,
    result_serializer=_settings.celery.result_serializer,
    timezone=_settings.celery.timezone,
    enable_utc=_settings.celery.enable_utc,
    
    task_routes=_settings.celery.task_routes,
    worker_prefetch_multiplier=_settings.celery.worker_prefetch_multiplier,
    task_acks_late=_settings.celery.task_acks_late,
    worker_disable_rate_limits=_settings.celery.worker_disable_rate_limits,
    task_always_eager=_settings.celery.task_always_eager,
    task_eager_propagates=_settings.celery.task_eager_propagates,  
    task_max_retries=_settings.celery.task_max_retries,
    task_time_limit=_settings.celery.task_time_limit,  
    task_soft_time_limit=_settings.celery.task_soft_time_limit,  
    result_expires=_settings.celery.result_expires,  
    result_persistent=_settings.celery.result_persistent,
)