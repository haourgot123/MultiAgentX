import mimetypes
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Sequence

from fastapi import UploadFile
from loguru import logger
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import Request
from backend.api.files.model import StoredFile
from backend.api.data_ingestion.model import IngestionStatus
from backend.config.settings import _settings
from backend.databases.db import get_utc_now
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.utils.blob_storage import blob_storage_client
from backend.utils.constants import Message
from backend.utils.retention import mark_for_retention_delete



class FileService:
    def __init__(self):
        self._tmp_root = (
            Path(_settings.process_file.root_download_folder).resolve() / "uploads" / "tmp"
        )
        self._office_suffixes = {
            ".doc",
            ".docx",
            ".docm",
            ".xls",
            ".xlsx",
            ".xlsm",
            ".ppt",
            ".pptx",
            ".pptm",
            ".odt",
            ".ods",
            ".odp",
            ".rtf",
        }

    @staticmethod
    def _get_log_prefix(request: Request | None = None, user_id: int | None = None) -> str:
        request_id = getattr(getattr(request, "state", None), "request_id", "-")
        resolved_user_id = (
            user_id
            if user_id is not None
            else getattr(getattr(request, "state", None), "user_id", "-")
        )
        return f"[FileService][request_id={request_id}][user_id={resolved_user_id}]"

    @staticmethod
    def _normalize_filename(filename: str | None) -> str:
        cleaned_name = Path(filename or "untitled").name.strip()
        if not cleaned_name:
            cleaned_name = "untitled"
        return cleaned_name[:255]

    def _get_user_file(
        self,
        db_session: Session,
        user_id: int,
        file_id: int,
        log_prefix: str,
    ) -> StoredFile:
        stored_file = (
            db_session.query(StoredFile)
            .filter(
                StoredFile.id == file_id,
                StoredFile.user_id == user_id,
                StoredFile.deleted_at.is_(None),
            )
            .first()
        )
        if not stored_file:
            logger.warning(f"{log_prefix} File not found")
            raise ObjectNotFoundException(message=Message.MESSAGE_FILE_NOT_FOUND)
        return stored_file

    def list_files(self, request: Request, db_session: Session, user_id: int) -> list[StoredFile]:
        log_prefix = self._get_log_prefix(request, user_id)
        files = (
            db_session.query(StoredFile)
            .filter(
                StoredFile.user_id == user_id,
                StoredFile.deleted_at.is_(None),
            )
            .order_by(StoredFile.created_at.desc())
            .all()
        )
        logger.debug(f"{log_prefix} Listed files successfully, count={len(files)}")
        return files

    def get_file(
        self, request: Request, db_session: Session, user_id: int, file_id: int
    ) -> StoredFile:
        log_prefix = self._get_log_prefix(request, user_id)
        stored_file = self._get_user_file(db_session, user_id, file_id, log_prefix)
        return stored_file

    def get_sas_url(self, stored_file: StoredFile) -> str:
        """Generate a fresh SAS URL for *stored_file*."""
        return blob_storage_client.generate_sas_url(stored_file.storage_path)

    def get_sas_expiry(self) -> str:
        """Return the ISO-8601 expiry datetime for a SAS URL generated now."""
        return blob_storage_client.generate_sas_expiry().isoformat()

    def _should_convert_to_pdf(self, path: Path) -> bool:
        return path.suffix.lower() in self._office_suffixes

    def _convert_to_pdf(self, input_path: Path, log_prefix: str) -> tuple[Path, str, str]:
        soffice_path = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice_path:
            raise InvalidRequestException(
                message="LibreOffice is not installed. Please install `soffice` on the server."
            )

        convert_command = [
            soffice_path,
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--convert-to",
            "pdf",
            "--outdir",
            str(input_path.parent),
            str(input_path),
        ]
        result = subprocess.run(
            convert_command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error(
                f"{log_prefix} LibreOffice conversion failed. "
                f"command={' '.join(convert_command)} stderr={result.stderr.strip()}"
            )
            raise InvalidRequestException(
                message=f"Failed to convert `{input_path.name}` to PDF"
            )

        converted_path = input_path.with_suffix(".pdf")
        if not converted_path.exists():
            raise InvalidRequestException(
                message=f"Converted PDF not found for `{input_path.name}`"
            )

        converted_name = f"{input_path.stem}.pdf"
        logger.debug(f"{log_prefix} Converted office file to PDF: {converted_name}")
        return converted_path, converted_name, "application/pdf"

    async def upload_files(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        uploaded_files: Sequence[UploadFile],
    ) -> list[StoredFile]:
        log_prefix = self._get_log_prefix(request, user_id)
        if not uploaded_files:
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_REQUEST)
        logger.info(f"{log_prefix} Uploading files, count={len(uploaded_files)}")

        # Temp directory for office→PDF conversion (cleaned up per file)
        tmp_dir = self._tmp_root / str(user_id)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        created_files: list[StoredFile] = []

        try:
            for uploaded_file in uploaded_files:
                original_name = self._normalize_filename(uploaded_file.filename)
                extension = Path(original_name).suffix
                stored_name = f"{uuid.uuid4().hex}{extension}"
                tmp_path = tmp_dir / stored_name

                # Write to local temp file (needed for office→PDF conversion)
                with tmp_path.open("wb") as output:
                    shutil.copyfileobj(uploaded_file.file, output)
                logger.debug(f"{log_prefix} Saved uploaded file to local temp: {tmp_path}")

                mime_type = uploaded_file.content_type or mimetypes.guess_type(
                    original_name
                )[0]
                final_tmp_path = tmp_path
                final_name = original_name
                final_mime_type = mime_type or "application/octet-stream"
                final_stored_name = stored_name

                if self._should_convert_to_pdf(tmp_path):
                    logger.debug(f"{log_prefix} Detected office file, converting to PDF")
                    converted_path, converted_name, converted_mime_type = (
                        self._convert_to_pdf(tmp_path, log_prefix)
                    )
                    final_tmp_path = converted_path
                    final_name = converted_name
                    final_mime_type = converted_mime_type
                    final_stored_name = f"{Path(stored_name).stem}.pdf"
                    # Remove original office temp file
                    if tmp_path.exists() and tmp_path != converted_path:
                        tmp_path.unlink(missing_ok=True)

                file_size = final_tmp_path.stat().st_size

                # Upload to Azure Blob Storage
                with final_tmp_path.open("rb") as f:
                    blob_path = blob_storage_client.upload_file(
                        user_id=user_id,
                        stored_name=final_stored_name,
                        data=f,
                        content_type=final_mime_type,
                    )
                logger.debug(f"{log_prefix} Uploaded file to blob storage path={blob_path}")

                # Clean up local temp file
                final_tmp_path.unlink(missing_ok=True)

                now = get_utc_now()
                db_file = StoredFile(
                    user_id=user_id,
                    name=final_name,
                    storage_path=blob_path,
                    mime_type=final_mime_type,
                    size=file_size,
                    ingestion_status=IngestionStatus.PENDING.value,
                    ingestion_error=None,
                    ingested_chunks=0,
                    ingested_at=None,
                    created_at=now,
                    updated_at=now,
                )
                db_session.add(db_file)
                created_files.append(db_file)
                logger.debug(
                    f"{log_prefix} Prepared DB row for uploaded file "
                    f"name={final_name} mime_type={final_mime_type} size={file_size}"
                )

            db_session.commit()
            for db_file in created_files:
                db_session.refresh(db_file)
            created_file_ids = [created_file.id for created_file in created_files]
            logger.info(
                f"{log_prefix} Upload completed successfully, created_file_ids={created_file_ids}"
            )
            return created_files
        except SQLAlchemyError as e:
            logger.exception(f"{log_prefix} Database error while uploading files: {e}")
            db_session.rollback()
            raise e
        finally:
            for uploaded_file in uploaded_files:
                await uploaded_file.close()

    def rename_file(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        file_id: int,
        new_name: str,
    ) -> StoredFile:
        log_prefix = self._get_log_prefix(request, user_id)
        stored_file = self._get_user_file(db_session, user_id, file_id, log_prefix)
        original_name = stored_file.name
        stored_file.name = self._normalize_filename(new_name)
        stored_file.updated_at = get_utc_now()
        db_session.commit()
        db_session.refresh(stored_file)
        logger.info(
            f"{log_prefix} Renamed file from '{original_name}' to '{stored_file.name}'"
        )
        return stored_file

    def delete_file(
        self, request: Request, db_session: Session, user_id: int, file_id: int
    ) -> dict:
        log_prefix = self._get_log_prefix(request, user_id)
        stored_file = self._get_user_file(db_session, user_id, file_id, log_prefix)
        from backend.api.conversation.model import Conversation, conversation_files

        attached_conversation_count = (
            db_session.query(func.count(Conversation.id))
            .join(
                conversation_files,
                conversation_files.c.conversation_id == Conversation.id,
            )
            .filter(
                Conversation.user_id == user_id,
                Conversation.chat_type == "file",
                Conversation.deleted_at.is_(None),
                conversation_files.c.file_id == stored_file.id,
            )
            .scalar()
        )
        if attached_conversation_count:
            raise InvalidRequestException(
                message="This file is attached to an active conversation and cannot be deleted."
            )

        now = get_utc_now()
        logger.info(f"{log_prefix} Soft deleting file; blob/vector purge deferred")

        mark_for_retention_delete(stored_file, now)
        db_session.commit()

        logger.info(
            f"{log_prefix} Soft deleted file successfully; purge_after={stored_file.purge_after}"
        )

        return {"message": Message.MESSAGE_FILE_DELETED_SUCCESSFULLY}


file_service = FileService()
