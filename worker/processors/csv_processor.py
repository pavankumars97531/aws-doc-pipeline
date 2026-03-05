import csv
import io
from core.logging import get_logger

logger = get_logger(__name__)


def process_csv(file_bytes: bytes, filename: str) -> dict:
    try:
        text = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)

        result = {
            "filename": filename,
            "row_count": len(rows),
            "columns": reader.fieldnames,
            "status": "processed",
        }
        logger.info({"action": "csv_processed", "filename": filename, "rows": len(rows)})
        return result
    except Exception as e:
        logger.error({"action": "csv_processing_failed", "filename": filename, "error": str(e)})
        raise