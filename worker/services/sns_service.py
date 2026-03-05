import boto3
import json
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)
sns_client = boto3.client("sns", region_name=settings.AWS_REGION)

def send_completion_notification(filename: str, result_key: str, status: str):
    message = {
        "status": status,
        "filename": filename,
        "result_location": result_key,
    }
    sns_client.publish(
        TopicArn=settings.SNS_TOPIC_ARN,
        Subject=f"Document Processing {status.upper()}: {filename}",
        Message=json.dumps(message, indent=2)
    )
    logger.info({"action": "sns_notification_sent", "filename": filename, "status": status})