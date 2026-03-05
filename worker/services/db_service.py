import psycopg2
import json
from datetime import datetime
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

def get_connection():
    return psycopg2.connect(
        host=settings.DB_HOST,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        port=5432,
        connect_timeout=5
    )

def init_db():
    """Create the jobs table if it doesn't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS processing_jobs (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            s3_key VARCHAR(500) NOT NULL,
            file_type VARCHAR(50),
            status VARCHAR(50) DEFAULT 'processing',
            result_key VARCHAR(500),
            error_message TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    logger.info({"action": "db_initialized"})

def record_job_start(filename: str, s3_key: str, file_type: str) -> int:
    """Insert a new job record, return the job ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO processing_jobs (filename, s3_key, file_type, status)
           VALUES (%s, %s, %s, 'processing') RETURNING id""",
        (filename, s3_key, file_type)
    )
    job_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    logger.info({"action": "job_started", "job_id": job_id, "filename": filename})
    return job_id

def record_job_complete(job_id: int, result_key: str):
    """Mark a job as completed."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE processing_jobs
           SET status='completed', result_key=%s, completed_at=NOW()
           WHERE id=%s""",
        (result_key, job_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.info({"action": "job_completed", "job_id": job_id})

def record_job_failed(job_id: int, error: str):
    """Mark a job as failed."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE processing_jobs
           SET status='failed', error_message=%s, completed_at=NOW()
           WHERE id=%s""",
        (error[:500], job_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.info({"action": "job_failed", "job_id": job_id, "error": error})