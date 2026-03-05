from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from services.s3_service import upload_file_to_s3
from services.sqs_service import send_processing_message
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "text/csv": "csv",
    "image/png": "image",
    "image/jpeg": "image",
}


@router.post("/upload", status_code=202)
async def upload_document(file: UploadFile = File(...)):
    """
    Accept a file upload.
    Returns 202 Accepted immediately — processing is async.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}"
        )

    file_bytes = await file.read()

    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=413, detail="File too large. Max 10MB.")

    file_type = ALLOWED_TYPES[file.content_type]

    # Upload to S3
    s3_key = upload_file_to_s3(file_bytes, file.filename, file.content_type)

    # NOTE: S3 event notification will auto-trigger SQS.
    # We also send manually here so we can include metadata SQS event won't have.
    message_id = send_processing_message(s3_key, file.filename, file_type)

    logger.info({
        "action": "upload_accepted",
        "filename": file.filename,
        "s3_key": s3_key,
        "message_id": message_id
    })

    return JSONResponse({
        "status": "accepted",
        "message": "File is being processed asynchronously.",
        "s3_key": s3_key,
        "message_id": message_id,
    })