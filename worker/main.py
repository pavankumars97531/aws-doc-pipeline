import boto3
import json
import time
from core.config import settings
from core.logging import get_logger
from services.s3_service import download_file, upload_result
from services.sns_service import send_completion_notification
from processors.pdf_processor import process_pdf
from processors.csv_processor import process_csv

logger = get_logger("worker.main")
sqs_client = boto3.client("sqs", region_name=settings.AWS_REGION)

PROCESSORS = {
    "pdf": process_pdf,
    "csv": process_csv,
}


def process_message(message: dict):
    body = json.loads(message["Body"])
    s3_key = body["s3_key"]
    filename = body["filename"]
    file_type = body["file_type"]

    job_id = None

    # Record job start in DB (if DB configured)
    if settings.DB_HOST:
        job_id = record_job_start(filename, s3_key, file_type)

    try:
        file_bytes = download_file(settings.S3_UPLOAD_BUCKET, s3_key)

        processor = PROCESSORS.get(file_type)
        if not processor:
            raise ValueError(f"No processor for file type: {file_type}")

        result = processor(file_bytes, filename)
        result_key = s3_key.replace("uploads/", "results/") + ".json"
        upload_result(json.dumps(result, indent=2), result_key)
        send_completion_notification(filename, result_key, "completed")

        if job_id and settings.DB_HOST:
            record_job_complete(job_id, result_key)

        logger.info({"action": "processing_complete", "filename": filename})

    except Exception as e:
        if job_id and settings.DB_HOST:
            record_job_failed(job_id, str(e))
        raise  # re-raise so SQS keeps the message for retry


def run_worker():
    logger.info({"action": "worker_start", "queue": settings.SQS_QUEUE_URL})

    while True:
        try:
            # Long poll — waits up to 20s for messages (saves API calls + cost)
            response = sqs_client.receive_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                MaxNumberOfMessages=1,  # Process one at a time for MVP
                WaitTimeSeconds=20,  # Long polling
                VisibilityTimeout=60,  # Must match queue setting
            )

            messages = response.get("Messages", [])

            if not messages:
                logger.info({"action": "queue_empty", "message": "No messages, polling..."})
                continue

            message = messages[0]
            receipt_handle = message["ReceiptHandle"]

            try:
                process_message(message)

                # SUCCESS — delete the message from queue
                sqs_client.delete_message(
                    QueueUrl=settings.SQS_QUEUE_URL,
                    ReceiptHandle=receipt_handle
                )
                logger.info({"action": "message_deleted", "message_id": message["MessageId"]})

            except Exception as e:
                # FAILURE — do NOT delete message. SQS will retry.
                # After max_receives (3), it goes to DLQ automatically.
                logger.error({
                    "action": "message_processing_failed",
                    "message_id": message["MessageId"],
                    "error": str(e),
                    "note": "Message will be retried or sent to DLQ"
                })
                # Sleep briefly to avoid hammering on repeated failures
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info({"action": "worker_shutdown"})
            break
        except Exception as e:
            logger.error({"action": "worker_loop_error", "error": str(e)})
            time.sleep(10)


if __name__ == "__main__":
    run_worker()