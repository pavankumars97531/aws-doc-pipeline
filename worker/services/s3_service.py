import boto3
from core.config import settings

s3_client = boto3.client("s3", region_name=settings.AWS_REGION)

def download_file(bucket: str, key: str) -> bytes:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()

def upload_result(data: str, result_key: str):
    s3_client.put_object(
        Bucket=settings.S3_RESULTS_BUCKET,
        Key=result_key,
        Body=data.encode("utf-8"),
        ContentType="application/json"
    )