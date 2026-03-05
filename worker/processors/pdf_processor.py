import io
from core.logging import get_logger

logger = get_logger(__name__)


def process_pdf(file_bytes: bytes, filename: str) -> dict:
    """
    Basic PDF processing — extracts metadata.
    In production: use pdfplumber, PyMuPDF, or AWS Textract.
    """
    try:
        # Minimal processing for MVP — just confirm it's a valid PDF
        if not file_bytes.startswith(b"%PDF"):
            raise ValueError("Not a valid PDF file")

        result = {
            "filename": filename,
            "size_bytes": len(file_bytes),
            "status": "processed",
            "page_count": "unknown",  # Add pdfplumber in Phase 2
            "extraction_method": "basic_validation",
        }
        logger.info({"action": "pdf_processed", "filename": filename})
        return result
    except Exception as e:
        logger.error({"action": "pdf_processing_failed", "filename": filename, "error": str(e)})
        raise