import os
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, status, File, UploadFile
from ..services.migrate_service import svc_migration_s3, svc_upgrade_pgdatabase_revisions, svc_downgrade_pgdatabase_revisions
from ..schemas.migrate_schema import MigrationS3Request, MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/migration", tags=["Migrate"])

@router.post("/s3", status_code=status.HTTP_200_OK, description="Migrate data from S3 to Qdrant")
async def migration_s3(
    request: MigrationS3Request, 
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    try:
        background_tasks.add_task(svc_migration_s3, request)
        return MessageResponse(status_code=status.HTTP_200_OK, message="S3 migration started")
    except Exception as e:
        logger.error(f"Error migrating S3: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.post('/pgdatabase/revisions/upgrade', status_code=status.HTTP_200_OK, description="Upgrade pgdatabase revisions")
async def upgrade_pgdatabase_revisions(
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    try:
        background_tasks.add_task(svc_upgrade_pgdatabase_revisions)
        return MessageResponse(status_code=status.HTTP_200_OK, message="PGDatabase revisions upgraded")
    except Exception as e:
        logger.error(f"Error upgrading PGDatabase revisions: {e}")  
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/pgdatabase/revisions/downgrade', status_code=status.HTTP_200_OK, description="Downgrade pgdatabase revisions")
async def downgrade_pgdatabase_revisions(
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    try:
        background_tasks.add_task(svc_downgrade_pgdatabase_revisions)
        return MessageResponse(status_code=status.HTTP_200_OK, message="PGDatabase revisions downgraded")
    except Exception as e:
        logger.error(f"Error downgrading PGDatabase revisions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post('/pgdatabase/tables/{table_name}/migrate', status_code=status.HTTP_200_OK, description="Migrate table from pgdatabase to qdrant")
async def migrate_table(
    table_name: str,
    file: UploadFile = File(..., description="The file to migrate"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    try:
        background_tasks.add_task(svc_migrate_table, table_name, file)
        return MessageResponse(status_code=status.HTTP_200_OK, message=f"Table {table_name} migrated")
    except Exception as e:
        logger.error(f"Error migrating table {table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
