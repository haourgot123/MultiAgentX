import mimetypes
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Sequence

from fastapi import UploadFile
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.api.files.model import StoredFile
from backend.api.data_ingestion.model import IngestionStatus
from backend.config.settings import _settings
from backend.databases.db import get_utc_now
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.utils.constants import Message


class FileService:
    def __init__(self):
        self.upload_root = (
            Path(_settings.process_file.root_download_folder).resolve() / "uploads"
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
    def _normalize_filename(filename: str | None) -> str:
        cleaned_name = Path(filename or "untitled").name.strip()
        if not cleaned_name:
            cleaned_name = "untitled"
        return cleaned_name[:255]

    def _get_user_file(self, db_session: Session, user_id: int, file_id: int) -> StoredFile:
        stored_file = (
            db_session.query(StoredFile)
            .filter(StoredFile.id == file_id, StoredFile.user_id == user_id)
            .first()
        )
        if not stored_file:
            raise ObjectNotFoundException(message=Message.MESSAGE_FILE_NOT_FOUND)
        return stored_file

    def list_files(self, db_session: Session, user_id: int) -> list[StoredFile]:
        return (
            db_session.query(StoredFile)
            .filter(StoredFile.user_id == user_id)
            .order_by(StoredFile.created_at.desc())
            .all()
        )

    def get_file(self, db_session: Session, user_id: int, file_id: int) -> StoredFile:
        stored_file = self._get_user_file(db_session, user_id, file_id)
        if not Path(stored_file.storage_path).exists():
            raise ObjectNotFoundException(message=Message.MESSAGE_FILE_NOT_FOUND)
        return stored_file

    def _should_convert_to_pdf(self, path: Path) -> bool:
        return path.suffix.lower() in self._office_suffixes

    def _convert_to_pdf(self, input_path: Path) -> tuple[Path, str, str]:
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
                "LibreOffice conversion failed. command={} stderr={}",
                " ".join(convert_command),
                result.stderr.strip(),
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
        return converted_path, converted_name, "application/pdf"

    async def upload_files(
        self, db_session: Session, user_id: int, uploaded_files: Sequence[UploadFile]
    ) -> list[StoredFile]:
        if not uploaded_files:
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_REQUEST)

        upload_dir = self.upload_root / str(user_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        created_files: list[StoredFile] = []
        written_paths: list[Path] = []

        try:
            for uploaded_file in uploaded_files:
                original_name = self._normalize_filename(uploaded_file.filename)
                extension = Path(original_name).suffix
                stored_name = f"{uuid.uuid4().hex}{extension}"
                storage_path = upload_dir / stored_name

                with storage_path.open("wb") as output:
                    shutil.copyfileobj(uploaded_file.file, output)
                written_paths.append(storage_path)

                mime_type = uploaded_file.content_type or mimetypes.guess_type(
                    original_name
                )[0]
                final_storage_path = storage_path
                final_name = original_name
                final_mime_type = mime_type or "application/octet-stream"

                if self._should_convert_to_pdf(storage_path):
                    converted_path, converted_name, converted_mime_type = (
                        self._convert_to_pdf(storage_path)
                    )
                    final_storage_path = converted_path
                    final_name = converted_name
                    final_mime_type = converted_mime_type
                    if converted_path not in written_paths:
                        written_paths.append(converted_path)
                    if storage_path.exists() and storage_path != converted_path:
                        storage_path.unlink(missing_ok=True)

                file_size = final_storage_path.stat().st_size
                now = get_utc_now()

                db_file = StoredFile(
                    user_id=user_id,
                    name=final_name,
                    storage_path=str(final_storage_path),
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

            db_session.commit()
            for db_file in created_files:
                db_session.refresh(db_file)
            return created_files
        except PermissionError as e:
            db_session.rollback()
            for path in written_paths:
                if path.exists():
                    path.unlink(missing_ok=True)
            raise e
        except SQLAlchemyError as e:
            db_session.rollback()
            for path in written_paths:
                if path.exists():
                    path.unlink(missing_ok=True)
            raise e
        finally:
            for uploaded_file in uploaded_files:
                await uploaded_file.close()

    def rename_file(
        self, db_session: Session, user_id: int, file_id: int, new_name: str
    ) -> StoredFile:
        stored_file = self._get_user_file(db_session, user_id, file_id)
        stored_file.name = self._normalize_filename(new_name)
        stored_file.updated_at = get_utc_now()
        db_session.commit()
        db_session.refresh(stored_file)
        return stored_file

    def delete_file(self, db_session: Session, user_id: int, file_id: int) -> dict:
        stored_file = self._get_user_file(db_session, user_id, file_id)
        storage_path = Path(stored_file.storage_path)
        deleting_file_id = stored_file.id

        db_session.delete(stored_file)
        db_session.commit()

        try:
            from backend.api.data_ingestion.service import data_ingestion_service

            data_ingestion_service.delete_file_vectors(user_id=user_id, file_id=deleting_file_id)
        except Exception as e:
            logger.warning(
                "Failed to remove vectors in Milvus for file_id={}: {}",
                deleting_file_id,
                e,
            )

        if storage_path.exists():
            try:
                storage_path.unlink(missing_ok=True)
            except OSError as e:
                logger.warning(f"Unable to remove file from disk: {storage_path}. {e}")

        return {"message": Message.MESSAGE_FILE_DELETED_SUCCESSFULLY}


file_service = FileService()
