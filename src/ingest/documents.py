"""
Document intake for the analyst.

One entry point — :func:`extract_document` — turns a PDF, image, spreadsheet or
text file into text plus candidate tables, with provenance. Digital PDFs use
their embedded text layer (free and exact); scanned pages and images go through
the lightweight OCR layer.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .ocr import OcrResult, lines_to_rows, ocr_image, rows_to_records

logger = logging.getLogger(__name__)

MAX_PAGES = 30
MAX_TABLE_ROWS = 5000
MAX_TEXT_CHARS = 200_000
_MIN_TEXT_PER_PAGE = 80
_RENDER_SCALE = 2.0


@dataclass(frozen=True)
class ExtractedTable:
    name: str
    records: Tuple[Dict[str, Any], ...]
    row_count: int
    source: str


@dataclass(frozen=True)
class ExtractedDocument:
    filename: str
    method: str
    page_count: int
    text: str
    tables: Tuple[ExtractedTable, ...]
    engine: Optional[str]
    mean_confidence: float
    page_engines: Tuple[str, ...]
    errors: Tuple[str, ...] = ()

    @property
    def has_text(self) -> bool:
        return bool(self.text.strip())


def _decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _from_dataframe(df: pd.DataFrame, name: str) -> ExtractedTable:
    records = df.head(MAX_TABLE_ROWS).to_dict(orient="records")
    return ExtractedTable(
        name=name,
        records=tuple(
            {str(k): (None if pd.isna(v) else v) for k, v in row.items()} for row in records
        ),
        row_count=int(len(df)),
        source=name,
    )


def _extract_pdf(data: bytes, filename: str) -> ExtractedDocument:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    page_count = min(len(reader.pages), MAX_PAGES)
    page_texts: List[str] = []
    for index in range(page_count):
        try:
            page_texts.append(reader.pages[index].extract_text() or "")
        except Exception as exc:  # pragma: no cover - malformed PDFs
            page_texts.append("")
            logger.warning("pypdf failed on page %d: %s", index, type(exc).__name__)

    joined = "\n\n".join(t for t in page_texts if t.strip())
    chars = len(joined.strip())
    digital = chars >= max(200, _MIN_TEXT_PER_PAGE * page_count)

    if digital:
        return ExtractedDocument(
            filename=filename,
            method="text_layer",
            page_count=page_count,
            text=joined[:MAX_TEXT_CHARS],
            tables=(),
            engine="pypdf",
            mean_confidence=1.0,
            page_engines=tuple(["pypdf"] * page_count),
        )

    return _extract_scanned_pdf(data, filename, page_count)


def _extract_scanned_pdf(data: bytes, filename: str, page_count: int) -> ExtractedDocument:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    texts: List[str] = []
    tables: List[ExtractedTable] = []
    confidences: List[float] = []
    engines: List[str] = []
    errors: List[str] = []

    for index in range(min(page_count, len(pdf))):
        try:
            bitmap = pdf[index].render(scale=_RENDER_SCALE).to_pil()
            result: OcrResult = ocr_image(bitmap)
        except Exception as exc:  # pragma: no cover - renderer failures
            errors.append(f"page {index + 1}: OCR failed ({type(exc).__name__})")
            continue
        texts.append(result.text)
        confidences.append(result.mean_confidence)
        engines.append(result.engine)

        records = rows_to_records(lines_to_rows(result.lines))
        if records:
            tables.append(
                ExtractedTable(
                    name=f"page_{index + 1}",
                    records=tuple(records[:MAX_TABLE_ROWS]),
                    row_count=len(records),
                    source="ocr",
                )
            )

    joined = "\n\n".join(t for t in texts if t.strip())
    return ExtractedDocument(
        filename=filename,
        method="ocr",
        page_count=page_count,
        text=joined[:MAX_TEXT_CHARS],
        tables=tuple(tables),
        engine=engines[0] if engines else None,
        mean_confidence=float(np.mean(confidences)) if confidences else 0.0,
        page_engines=tuple(engines),
        errors=tuple(errors),
    )


def extract_document(data: bytes, filename: str) -> ExtractedDocument:
    """
    Extract text and tables from a supported document.

    Raises :class:`ValueError` only when the type is unsupported; parse-level
    failures are reported in ``errors`` so the caller can surface them.
    """
    if not data:
        raise ValueError("The document is empty.")
    name = (filename or "document").lower()
    extension = "." + name.rsplit(".", 1)[-1] if "." in name else ""

    if extension == ".pdf":
        return _extract_pdf(data, name)

    if extension in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"):
        result = ocr_image(data)
        records = rows_to_records(lines_to_rows(result.lines))
        tables = (
            ExtractedTable(
                name="page_1",
                records=tuple(records[:MAX_TABLE_ROWS]),
                row_count=len(records),
                source="ocr",
            ),
        ) if records else ()
        return ExtractedDocument(
            filename=name,
            method="ocr",
            page_count=1,
            text=result.text[:MAX_TEXT_CHARS],
            tables=tables,
            engine=result.engine,
            mean_confidence=result.mean_confidence,
            page_engines=(result.engine,),
        )

    if extension == ".csv":
        df = pd.read_csv(io.BytesIO(data))
        table = _from_dataframe(df, "sheet")
        return ExtractedDocument(
            filename=name, method="table", page_count=1,
            text=df.head(100).to_csv(index=False)[:MAX_TEXT_CHARS],
            tables=(table,), engine="pandas", mean_confidence=1.0,
            page_engines=("pandas",),
        )

    if extension == ".parquet":
        df = pd.read_parquet(io.BytesIO(data))
        table = _from_dataframe(df, "table")
        return ExtractedDocument(
            filename=name, method="table", page_count=1,
            text=df.head(100).to_csv(index=False)[:MAX_TEXT_CHARS],
            tables=(table,), engine="pandas", mean_confidence=1.0,
            page_engines=("pandas",),
        )

    if extension in (".xlsx", ".xls"):
        df = pd.read_excel(io.BytesIO(data))
        table = _from_dataframe(df, "sheet_1")
        return ExtractedDocument(
            filename=name, method="table", page_count=1,
            text=df.head(100).to_csv(index=False)[:MAX_TEXT_CHARS],
            tables=(table,), engine="pandas", mean_confidence=1.0,
            page_engines=("pandas",),
        )

    if extension in (".txt", ".md", ".markdown", ".json", ".html", ".htm", ".xml"):
        return ExtractedDocument(
            filename=name, method="text", page_count=1,
            text=_decode_text(data)[:MAX_TEXT_CHARS],
            tables=(), engine=None, mean_confidence=1.0, page_engines=("text",),
        )

    raise ValueError(
        f"Unsupported document type '{extension or name}'. "
        "Supported: pdf, png, jpg, tif, bmp, webp, csv, parquet, xlsx, txt, md, json, html."
    )
