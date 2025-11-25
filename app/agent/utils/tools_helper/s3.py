from loguru import logger
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from app.config.settings import _settings
from .model import (
    S3ServiceGetPresignedURLModel,
    S3ServiceGetPresignedURLModelResponse,
    S3ServiceUploadFileWithBinaryModel,
    S3ServiceUploadFileWithFilePathModel,
    S3ServiceDeleteFileModel,
    MessageModelResponse,
)

class S3Service:

    def __init__(self) -> None:
        try:
            client_config = {
                "service_name": "s3",
                "aws_access_key_id": _settings.s3.access_key_id,
                "aws_secret_access_key": _settings.s3.secret_access_key,
                "region_name": _settings.s3.region,
            }
            if _settings.s3.endpoint:
                client_config["endpoint_url"] = _settings.s3.endpoint
            self.client = boto3.client(**client_config)
            self.bucket = _settings.s3.bucket_name
            
            if not self.bucket:
                raise ValueError("S3_BUCKET_NAME environment variable is required")
                
            # Test connection
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"S3Service initialized successfully for bucket: {self.bucket}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except ClientError as e:
            logger.error(f"Error initializing S3 client: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing S3Service: {e}")
            raise

    def get_presigned_url(self, input: S3ServiceGetPresignedURLModel) -> S3ServiceGetPresignedURLModelResponse:
        """Generate a presigned URL for a given key."""
        try:    
            return S3ServiceGetPresignedURLModelResponse(
                url=self.client.generate_presigned_url(
                    "get_object", 
                    Params={"Bucket": self.bucket, "Key": input.key}, 
                    ExpiresIn=input.expiration
                )
            )
        except Exception as e:
            logger.error(f"Error generating presigned URL for key {input.key}: {e}")
            return S3ServiceGetPresignedURLModelResponse(url=None)

    def upload_file(self, input: S3ServiceUploadFileWithBinaryModel) -> MessageModelResponse:
        """Upload a file to the bucket."""
        try:
            self.client.upload_fileobj(input.file, self.bucket, input.key)
            logger.info(f"Successfully uploaded file with key: {input.key}")
            return MessageModelResponse(message=f"Successfully uploaded file with key: {input.key}", success=True)
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            return MessageModelResponse(message=f"Error uploading file: {e}", success=False)
    
    def upload_file_path(self, input: S3ServiceUploadFileWithFilePathModel) -> MessageModelResponse:
        """Upload a file to the bucket from a local path."""
        try:
            self.client.upload_file(input.file_path, self.bucket, input.key)
            return MessageModelResponse(message=f"Successfully uploaded file {input.file_path} with key: {input.key}", success=True)
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            return MessageModelResponse(message=f"Error uploading file: {e}", success=False)
    
    def delete_file(self, input: S3ServiceDeleteFileModel) -> MessageModelResponse:
        """Delete a file from the bucket."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=input.key)
            logger.info(f"Successfully deleted file with key: {input.key}")
            return MessageModelResponse(message=f"Successfully deleted file with key: {input.key}", success=True)
        except Exception as e:
            logger.error(f"Unexpected error deleting file: {e}")
            return MessageModelResponse(message=f"Error deleting file: {e}", success=False)
