from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AWS_REGION: str = "us-east-1"
    S3_UPLOAD_BUCKET: str
    S3_RESULTS_BUCKET: str
    SQS_QUEUE_URL: str
    SNS_TOPIC_ARN: str
    DB_HOST: str = ""
    DB_NAME: str = "pipeline_db"
    DB_USER: str = "pipeline_user"
    DB_PASSWORD: str = ""
    USE_SECRETS_MANAGER: bool = False  # set True in production .env

    class Config:
        env_file = ".env"

settings = Settings()

# Override DB credentials from Secrets Manager if enabled
if settings.USE_SECRETS_MANAGER and settings.DB_HOST == "":
    from services.secrets_service import get_db_credentials
    creds = get_db_credentials()
    settings.DB_HOST = creds.get("DB_HOST", "")
    settings.DB_PASSWORD = creds.get("DB_PASSWORD", "")