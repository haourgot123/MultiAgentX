from __future__ import annotations

from datetime import datetime, timedelta

from backend.config.settings import _settings
from backend.databases.db import get_utc_now


def get_retention_delta() -> timedelta:
    return timedelta(days=max(0, _settings.data_retention.retention_days))


def get_purge_after(now: datetime | None = None) -> datetime:
    base_time = now or get_utc_now()
    return base_time + get_retention_delta()


def mark_for_retention_delete(obj, now: datetime | None = None) -> None:
    deleted_at = now or get_utc_now()
    if hasattr(obj, "deleted_at"):
        obj.deleted_at = deleted_at
    if hasattr(obj, "purge_after"):
        obj.purge_after = get_purge_after(deleted_at)
    if hasattr(obj, "purged_at"):
        obj.purged_at = None
    if hasattr(obj, "updated_at"):
        obj.updated_at = deleted_at
