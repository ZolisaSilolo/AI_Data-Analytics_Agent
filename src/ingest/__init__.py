"""Document intake: OCR, text-layer extraction and RAG chunking."""

from .chunking import TextChunk, chunk_text
from .documents import ExtractedDocument, ExtractedTable, extract_document
from .ocr import (
    OcrLine,
    OcrResult,
    engine_available,
    lines_to_rows,
    ocr_image,
    rows_to_records,
)

__all__ = [
    "ExtractedDocument",
    "ExtractedTable",
    "OcrLine",
    "OcrResult",
    "TextChunk",
    "chunk_text",
    "engine_available",
    "extract_document",
    "lines_to_rows",
    "ocr_image",
    "rows_to_records",
]
