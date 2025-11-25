import os
import httpx
import io
import logging
from typing import List, Dict, Any, IO
from app.config.settings import _settings
from fastapi import HTTPException



logger = logging.getLogger(__name__)


class FileHelper:
    
    @staticmethod
    async def download_file(
        file_url: str
    ) -> bytes:
        async with httpx.AsyncClient(timeout=_settings.process_file.download_timeout) as session:
            response = await session.get(file_url)
            if response.status_code != 200:
                logger.error(f"Failed to download file from {file_url}")
                raise HTTPException(status_code=400, detail=f"Failed to download file from {file_url}")
            return response.content

    @staticmethod
    def sort_file_by_size(
        files: List[Dict[str, Any]]
    ):
        files = sorted(files, key=lambda x: x["file_size"], reverse=False)
        return files
    
    @staticmethod
    def delete_folder_by_path(
        folder_path: str
    ):
        try:
            if os.path.exists(folder_path):
                os.rmdir(folder_path)
                logger.info(f"Folder {folder_path} deleted successfully")
            else:
                logger.error(f"Folder {folder_path} not found")
                raise FileNotFoundError(f"Folder {folder_path} not found")
        except Exception as e:
            logger.error(f"Error deleting folder {folder_path}: {e}")
            raise

    @staticmethod
    async def update_status_callback(
        kb_id: str,
        file_id: str,
        status: str,
        reason: str = ""
    ) -> None:
        api_url = f"{_settings.web.be_base_url}/api/knowledge/{kb_id}/file/{file_id}/process-callback"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_settings.web.authen_token}"
        }
        
        data = {"status": status, "reason": reason}

        async with httpx.AsyncClient(timeout=_settings.process_file.download_timeout) as session:
            response = await session.post(api_url, headers=headers, json=data)
            if response.status_code != 200:
                logger.error(f"Failed to update status callback for {kb_id}: {response.text}")
                raise HTTPException(status_code=400, detail=f"Failed to update status callback for {kb_id}")

            logger.info(f"Successfully updated status callback for {kb_id} -> {status}")
    
