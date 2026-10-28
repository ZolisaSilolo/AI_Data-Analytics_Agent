"""OCR intake: table reconstruction, chunking and document dispatch."""

from __future__ import annotations

import numpy as np
import pytest

from ingest import (
    OcrLine,
    chunk_text,
    extract_document,
    lines_to_rows,
    rows_to_records,
)


def _line(text, x, y, w=80.0, h=14.0, conf=0.99):
    return OcrLine(text=text, confidence=conf, bbox=(x, y, x + w, y + h))


def test_lines_to_rows_reconstructs_a_grid():
    lines = [
        _line("Region", 10, 10), _line("Revenue", 300, 10),
        _line("AMER", 10, 30), _line("4500", 300, 31),
        _line("EMEA", 10, 52), _line("1250", 300, 52),
    ]
    rows = lines_to_rows(lines)
    assert len(rows) == 3
    assert rows[0].cells == ("Region", "Revenue")
    assert rows[1].cells == ("AMER", "4500")

    records = rows_to_records(rows)
    assert records == [
        {"Region": "AMER", "Revenue": "4500"},
        {"Region": "EMEA", "Revenue": "1250"},
    ]


def test_lines_to_rows_collapses_unclear_grids():
    lines = [_line("just", 10, 10), _line("text", 12, 11)]
    rows = lines_to_rows(lines)
    assert rows and all(len(row.cells) == 1 for row in rows)


def test_chunk_text_is_deterministic_and_bounded():
    text = "word " * 500
    first = chunk_text(text, max_chars=200, overlap=40)
    second = chunk_text(text, max_chars=200, overlap=40)
    assert first == second
    assert all(len(chunk.text) <= 200 for chunk in first)
    assert [chunk.index for chunk in first] == list(range(len(first)))


def test_chunk_text_handles_short_and_empty():
    assert chunk_text("") == []
    assert len(chunk_text("hello")) == 1
    with pytest.raises(ValueError):
        chunk_text("x" * 100, max_chars=50, overlap=50)


def test_extract_document_csv():
    document = extract_document(b"region,revenue\nAMER,4500\nEMEA,1250\n", "report.csv")
    assert document.method == "table"
    assert document.tables[0].row_count == 2
    assert document.tables[0].records[0]["region"] == "AMER"


def test_extract_document_text():
    document = extract_document(b"hello analyst", "notes.txt")
    assert document.method == "text"
    assert document.text == "hello analyst"


def test_extract_document_unsupported_type():
    with pytest.raises(ValueError):
        extract_document(b"\x00\x01", "payload.bin")


def test_rapidocr_end_to_end_on_a_synthetic_image():
    rapidocr = pytest.importorskip("rapidocr_onnxruntime")  # noqa: F841
    from PIL import Image, ImageDraw

    from ingest.ocr import ocr_image

    image = Image.new("RGB", (480, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.text((16, 20), "Revenue AMER 4500", fill="black")
    draw.text((16, 60), "Revenue EMEA 1250", fill="black")

    result = ocr_image(np.array(image))
    text = result.text.replace(" ", "")
    assert "AMER" in text
    assert "4500" in text
    assert result.mean_confidence > 0.8
