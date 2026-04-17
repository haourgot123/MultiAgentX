"""Azure Blob Storage client for file upload, SAS URL generation, and deletion."""
from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO

from loguru import logger

from backend.config.settings import _settings

_logger = logger.bind(service="blob-storage")


class BlobStorageClient:
    """Wraps Azure Blob Storage operations used across the application."""

    def __init__(self) -> None:
        self._connection_string = _settings.azure_blob.connection_string
        self._account_name = _settings.azure_blob.account_name
        self._account_key = _settings.azure_blob.account_key
        self._container_name = _settings.azure_blob.container_name
        self._sas_expiry_hours = _settings.azure_blob.sas_expiry_hours
        self._client = None  # lazy-initialised

    def _get_client(self):
        """Return (and lazily create) the BlobServiceClient."""
        if self._client is not None:
            return self._client

        try:
            from azure.storage.blob import BlobServiceClient as _AzureBlobServiceClient
        except ImportError as exc:
            raise RuntimeError(
                "azure-storage-blob is not installed. "
                "Run: pip install azure-storage-blob>=12.0.0"
            ) from exc

        if not self._connection_string:
            raise RuntimeError(
                "Azure Blob Storage connection string is not configured. "
                "Set the BLOB-CONNECTION-STRING environment variable."
            )
        if not self._container_name:
            raise RuntimeError(
                "Azure Blob Storage container name is not configured. "
                "Set the BLOB-CONTAINER environment variable."
            )

        self._client = _AzureBlobServiceClient.from_connection_string(
            self._connection_string
        )

        # Ensure the container exists (create if not present)
        try:
            from azure.core.exceptions import ResourceExistsError

            self._client.create_container(self._container_name)
            _logger.info("Created Azure Blob container: {}", self._container_name)
        except ResourceExistsError:
            pass  # container already exists — nothing to do

        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload_file(
        self,
        user_id: int,
        stored_name: str,
        data: BinaryIO,
        content_type: str,
    ) -> str:
        """Upload *data* to blob storage and return the blob path.

        Args:
            user_id: Owner of the file (used to namespace blobs).
            stored_name: File name to use in blob storage (e.g. ``abc123.pdf``).
            data: File-like binary stream to upload.
            content_type: MIME type of the file.

        Returns:
            Blob path in the format ``uploads/{user_id}/{stored_name}``.
        """
        blob_path = f"uploads/{user_id}/{stored_name}"
        client = self._get_client()
        blob_client = client.get_blob_client(
            container=self._container_name, blob=blob_path
        )
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=self._make_content_settings(content_type),
        )
        _logger.debug(
            "Uploaded blob path={} content_type={}", blob_path, content_type
        )
        return blob_path

    def generate_sas_url(
        self,
        blob_path: str,
        expiry_hours: int | None = None,
    ) -> str:
        """Generate a read-only SAS URL for *blob_path*.

        Args:
            blob_path: Blob path returned by :meth:`upload_file`.
            expiry_hours: Override the configured expiry (default from settings).

        Returns:
            A fully-qualified HTTPS SAS URL that expires after *expiry_hours*.
        """
        from azure.storage.blob import (
            BlobSasPermissions,
            generate_blob_sas,
        )

        if not self._account_name or not self._account_key:
            raise RuntimeError(
                "Azure Storage account name and key are required for SAS URL generation. "
                "Set AZURE-ACCOUNT-NAME and AZURE-ACCOUNT-KEY environment variables."
            )

        hours = expiry_hours if expiry_hours is not None else self._sas_expiry_hours
        expiry = datetime.now(timezone.utc) + timedelta(hours=hours)

        sas_token = generate_blob_sas(
            account_name=self._account_name,
            container_name=self._container_name,
            blob_name=blob_path,
            account_key=self._account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
        )

        sas_url = (
            f"https://{self._account_name}.blob.core.windows.net"
            f"/{self._container_name}/{blob_path}?{sas_token}"
        )
        _logger.debug(
            "Generated SAS URL blob_path={} expires_at={}", blob_path, expiry.isoformat()
        )
        return sas_url

    def generate_sas_expiry(self, expiry_hours: int | None = None) -> datetime:
        """Return the UTC expiry datetime for a SAS URL generated now."""
        hours = expiry_hours if expiry_hours is not None else self._sas_expiry_hours
        return datetime.now(timezone.utc) + timedelta(hours=hours)

    def delete_blob(self, blob_path: str) -> None:
        """Delete a blob.  Silently ignores blobs that do not exist."""
        client = self._get_client()
        blob_client = client.get_blob_client(
            container=self._container_name, blob=blob_path
        )
        try:
            blob_client.delete_blob()
            _logger.debug("Deleted blob path={}", blob_path)
        except Exception as exc:
            # ResourceNotFound or transient errors — log and continue
            _logger.warning("Failed to delete blob path={}: {}", blob_path, exc)

    def download_to_temp_file(self, blob_path: str, suffix: str = "") -> Path:
        """Download a blob to a temporary local file.

        Returns:
            :class:`pathlib.Path` of the temp file.  The **caller** is
            responsible for deleting this file when done.
        """
        client = self._get_client()
        blob_client = client.get_blob_client(
            container=self._container_name, blob=blob_path
        )
        tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=suffix)
        tmp_path = Path(tmp_path_str)
        try:
            with open(tmp_fd, "wb") as tmp_file:
                download_stream = blob_client.download_blob()
                download_stream.readinto(tmp_file)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
        _logger.debug(
            "Downloaded blob path={} to temp file={}", blob_path, tmp_path
        )
        return tmp_path

    def upload_bytes(
        self,
        blob_path: str,
        data: BinaryIO,
        content_type: str,
    ) -> str:
        """Upload *data* to an explicit *blob_path* and return that path.

        Unlike :meth:`upload_file`, the caller controls the full blob path
        (e.g. ``skills/{user_id}/{name}.zip``).
        """
        client = self._get_client()
        blob_client = client.get_blob_client(
            container=self._container_name, blob=blob_path
        )
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=self._make_content_settings(content_type),
        )
        _logger.debug(
            "Uploaded blob path={} content_type={}", blob_path, content_type
        )
        return blob_path

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_content_settings(content_type: str):
        from azure.storage.blob import ContentSettings

        return ContentSettings(content_type=content_type)


blob_storage_client = BlobStorageClient()
