from fastapi import FastAPI
from routers.upload import router as upload_router
from core.logging import get_logger

logger = get_logger("api.startup")

app = FastAPI(
    title="Document Processing Pipeline API",
    description="Async document processing via S3 + SQS",
    version="1.0.0"
)

app.include_router(upload_router, prefix="/api/v1", tags=["uploads"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup():
    logger.info({"action": "api_startup", "message": "API is running"})