import os
import boto3
from tqdm import tqdm
from app.config.settings import _settings
from alembic import command
from alembic.config import Config
from loguru import logger
from fastapi import UploadFile

s3_resource = boto3.resource(
    "s3",
    region_name=_settings.s3.region,
    aws_access_key_id=_settings.s3.access_key_id,
    aws_secret_access_key=_settings.s3.secret_access_key,
    endpoint_url=_settings.s3.endpoint,
)

def svc_migration_s3(request):
    source_bucket = request.source_bucket
    target_bucket = request.target_bucket
    prefix = request.prefix
    source = s3_resource.Bucket(source_bucket)
    objects = list(source.objects.filter(Prefix=prefix))
    for obj in tqdm(objects, total=len(objects)):
        copy_source = {'Bucket': source_bucket, 'Key': obj.key}
        s3_resource.Object(target_bucket, obj.key).copy(copy_source)    
        


def get_alembic_cfg():
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", _settings.postgres.url)
    return alembic_cfg
        
def svc_upgrade_pgdatabase_revisions():
    alembic_cfg = get_alembic_cfg()
    command.upgrade(alembic_cfg, "head")
    logger.info("PGDatabase revisions upgraded")


def svc_downgrade_pgdatabase_revisions():   
    alembic_cfg = get_alembic_cfg()
    command.downgrade(alembic_cfg, "-1")
    logger.info("PGDatabase revisions downgraded")
    
    