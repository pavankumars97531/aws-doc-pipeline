import boto3
import json
from core.logging import get_logger

logger = get_logger(__name__)


def get_db_credentials() -> dict:
    """Fetch DB credentials from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name="us-east-1")

    try:
        response = client.get_secret_value(
            SecretId="doc-pipeline/db-credentials"
        )
        secret = json.loads(response["SecretString"])
        logger.info({"action": "secrets_fetched", "secret": "doc-pipeline/db-credentials"})
        return secret
    except Exception as e:
        logger.error({"action": "secrets_fetch_failed", "error": str(e)})
        raise