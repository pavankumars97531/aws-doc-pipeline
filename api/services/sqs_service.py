import boto3
import json
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

sqs_client = boto3.client("sqs", region_name=settings.AWS_REGION)


def send_processing_message(s3_key: str, filename: str, file_type: str) -> str:
    """Send a message to SQS to trigger processing."""
    message_body = {
        "s3_key": s3_key,
        "filename": filename,
        "file_type": file_type,
    }

    try:
        response = sqs_client.send_message(
            QueueUrl=settings.SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body),
            # MessageGroupId only needed for FIFO queues
        )
        message_id = response["MessageId"]
        logger.info({"action": "sqs_message_sent", "message_id": message_id, "s3_key": s3_key})
        return message_id
    except Exception as e:
        logger.error({"action": "sqs_send_failed", "error": str(e)})
        raise