import boto3
from botocore.exceptions import ClientError
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

s3_client = boto3.client("s3", region_name=settings.AWS_REGION)


def upload_file_to_s3(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Upload file to S3 and return the S3 key."""
    import uuid
    key = f"uploads/{uuid.uuid4()}/{filename}"

    try:
        s3_client.put_object(
            Bucket=settings.S3_UPLOAD_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        logger.info({"action": "s3_upload_success", "key": key, "bucket": settings.S3_UPLOAD_BUCKET})
        return key
    except ClientError as e:
        logger.error({"action": "s3_upload_failed", "error": str(e)})
        raise