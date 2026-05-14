from __future__ import annotations

import io
import mimetypes
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from backend.api.conversation.model import Conversation
from backend.api.files.model import StoredFile
from backend.api.skills.model import AgentSkill
from backend.config.settings import _settings
from backend.databases.db import get_utc_now
from backend.utils.blob_storage import blob_storage_client
from backend.utils.retention import get_retention_delta



class DataRetentionService:
    """Retention jobs for resources that user-facing APIs soft-delete."""

    @staticmethod
    def _coerce_for_compare(value, now):
        if value is not None and getattr(value, "tzinfo", None) is None and now.tzinfo:
            return value.replace(tzinfo=now.tzinfo)
        return value

    def _is_due_for_purge(self, obj: Any, now, *, mutate_missing: bool) -> bool:
        deleted_at = self._coerce_for_compare(getattr(obj, "deleted_at", None), now)
        if deleted_at is None or getattr(obj, "purged_at", None) is not None:
            return False

        purge_after = self._coerce_for_compare(getattr(obj, "purge_after", None), now)
        if purge_after is None:
            purge_after = deleted_at + get_retention_delta()
            if mutate_missing:
                obj.purge_after = purge_after

        return purge_after <= now

    def _due_records(self, db_session: Session, model, now, batch_size: int):
        candidates = (
            db_session.query(model)
            .filter(model.deleted_at.isnot(None), model.purged_at.is_(None))
            .order_by(model.deleted_at.asc())
            .limit(batch_size)
            .all()
        )
        return [
            obj
            for obj in candidates
            if self._is_due_for_purge(obj, now, mutate_missing=True)
        ]

    @staticmethod
    def _mark_purged(obj, now) -> None:
        if hasattr(obj, "purged_at"):
            obj.purged_at = now
        if hasattr(obj, "updated_at"):
            obj.updated_at = now

    @staticmethod
    def _delete_blob(blob_path: str | None) -> bool:
        if not blob_path:
            return False
        blob_storage_client.delete_blob(blob_path)
        return True

    def purge_due_records(
        self,
        db_session: Session,
        *,
        batch_size: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Purge external resources for soft-deleted rows whose retention expired."""

        now = get_utc_now()
        effective_batch_size = batch_size or _settings.data_retention.purge_batch_size
        result: dict[str, Any] = {
            "dry_run": dry_run,
            "retention_days": _settings.data_retention.retention_days,
            "batch_size": effective_batch_size,
            "tables": {},
        }

        files = self._due_records(db_session, StoredFile, now, effective_batch_size)
        result["tables"]["FileAsset"] = {"eligible": len(files), "purged": 0}
        for stored_file in files:
            if not dry_run:
                try:
                    from backend.api.data_ingestion.service import data_ingestion_service

                    data_ingestion_service.delete_file_vectors(
                        user_id=stored_file.user_id,
                        file_id=stored_file.id,
                    )
                except Exception as exc:
                    logger.warning(
                        "[DataRetentionService] Vector purge failed for file_id={}: {}",
                        stored_file.id,
                        exc,
                    )
                try:
                    self._delete_blob(stored_file.storage_path)
                except Exception as exc:
                    logger.warning(
                        "[DataRetentionService] Blob purge failed for file_id={} path={}: {}",
                        stored_file.id,
                        stored_file.storage_path,
                        exc,
                    )
                self._mark_purged(stored_file, now)
                result["tables"]["FileAsset"]["purged"] += 1

        skills = self._due_records(db_session, AgentSkill, now, effective_batch_size)
        result["tables"]["AgentSkill"] = {"eligible": len(skills), "purged": 0}
        for skill in skills:
            if not dry_run:
                try:
                    self._delete_blob(skill.blob_path)
                except Exception as exc:
                    logger.warning(
                        "[DataRetentionService] Skill blob purge failed skill_id={} path={}: {}",
                        skill.id,
                        skill.blob_path,
                        exc,
                    )
                storage_path = Path(str(skill.storage_path))
                if storage_path.exists():
                    try:
                        if storage_path.is_dir():
                            shutil.rmtree(storage_path)
                        else:
                            storage_path.unlink(missing_ok=True)
                    except OSError as exc:
                        logger.warning(
                            "[DataRetentionService] Skill blob purge failed skill_id={} path={}: {}",
                            skill.id,
                            storage_path,
                            exc,
                        )
                self._mark_purged(skill, now)
                result["tables"]["AgentSkill"]["purged"] += 1

        conversations = self._due_records(
            db_session,
            Conversation,
            now,
            effective_batch_size,
        )
        result["tables"]["Conversation"] = {
            "eligible": len(conversations),
            "purged": 0,
        }
        for conversation in conversations:
            if not dry_run:
                for message in conversation.messages:
                    try:
                        self._delete_blob(message.blob_path)
                    except Exception as exc:
                        logger.warning(
                            "[DataRetentionService] Message blob purge failed message_id={} path={}: {}",
                            message.id,
                            message.blob_path,
                            exc,
                        )
                self._mark_purged(conversation, now)
                result["tables"]["Conversation"]["purged"] += 1

        if dry_run:
            db_session.rollback()
        else:
            db_session.commit()

        return result

    @staticmethod
    def _skill_payload(skill: AgentSkill) -> tuple[io.BytesIO, str, str]:
        storage_path = Path(str(skill.storage_path))
        if not storage_path.exists():
            raise FileNotFoundError(f"Skill storage path not found: {storage_path}")

        if storage_path.is_dir():
            payload = io.BytesIO()
            with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(storage_path.rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(storage_path))
            payload.seek(0)
            return payload, "application/zip", ".zip"

        payload = io.BytesIO(storage_path.read_bytes())
        content_type = mimetypes.guess_type(storage_path.name)[0] or "application/octet-stream"
        return payload, content_type, storage_path.suffix or ".bin"

    def backfill_skill_blob_paths(
        self,
        db_session: Session,
        *,
        batch_size: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Upload local skill packages to blob storage when blob_path is missing."""

        effective_batch_size = (
            batch_size or _settings.data_retention.skill_blob_backfill_batch_size
        )
        skills = (
            db_session.query(AgentSkill)
            .filter(
                AgentSkill.deleted_at.is_(None),
                AgentSkill.blob_path.is_(None),
            )
            .order_by(AgentSkill.created_at.asc())
            .limit(effective_batch_size)
            .all()
        )
        result = {
            "dry_run": dry_run,
            "eligible": len(skills),
            "uploaded": 0,
            "skipped": 0,
            "errors": [],
        }
        now = get_utc_now()

        for skill in skills:
            try:
                payload, content_type, suffix = self._skill_payload(skill)
                blob_key = (
                    f"skills/{skill.user_id}/backfill/"
                    f"{skill.id}_{uuid.uuid4().hex}{suffix}"
                )
                if not dry_run:
                    skill.blob_path = blob_storage_client.upload_bytes(
                        blob_path=blob_key,
                        data=payload,
                        content_type=content_type,
                    )
                    skill.updated_at = now
                result["uploaded"] += 1
            except Exception as exc:
                result["skipped"] += 1
                result["errors"].append({"skill_id": skill.id, "error": str(exc)})

        if dry_run:
            db_session.rollback()
        else:
            db_session.commit()

        return result


data_retention_service = DataRetentionService()
