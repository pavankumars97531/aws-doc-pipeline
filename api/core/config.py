from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AWS_REGION: str = "us-east-1"
    S3_UPLOAD_BUCKET: str
    SQS_QUEUE_URL: str

    class Config:
        env_file = ".env"


settings = Settings()