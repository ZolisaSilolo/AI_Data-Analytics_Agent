"""
Lightweight OCR layer for the analyst intake.

Design rules (mirrors the rest of the platform):

* Cheap first. Digital PDFs are read from their text layer; OCR is only used
  for scanned pages and images.
* Open-source only. The default engine is RapidOCR (PP-OCR, ONNX Runtime),
  which runs on CPU in a Lambda with no GPU, no Docker and ~15 MB of models.
* The output of OCR is *evidence* (text, lines, tables) for ingestion and RAG.
  It is never treated as a source of numbers for the narrative; those go
  through the deterministic engine like everything else.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class OcrLine:
    text: str
    confidence: float
    bbox: BBox
    page: int = 0


@dataclass(frozen=True)
class OcrResult:
    lines: Tuple[OcrLine, ...]
    engine: str
    duration_ms: int
    mean_confidence: float
    width: int = 0
    height: int = 0

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines if line.text)


class OcrEngine(Protocol):
    name: str

    def recognize(self, image: np.ndarray) -> List[OcrLine]: ...


def _to_bbox(points: Sequence[Sequence[float]]) -> BBox:
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


class RapidOcrEngine:
    """RapidOCR (PP-OCRv5) via ONNX Runtime. Loaded lazily, reused per process."""

    name = "rapidocr"

    def __init__(self) -> None:
        self._engine: Any = None

    def _load(self) -> Any:
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR  # local, optional dependency

            self._engine = RapidOCR()
            logger.info("Loaded RapidOCR models")
        return self._engine

    def recognize(self, image: np.ndarray) -> List[OcrLine]:
        engine = self._load()
        rows, _elapsed = engine(image)
        lines: List[OcrLine] = []
        for row in rows or []:
            points, text, score = row
            text = str(text).strip()
            if not text:
                continue
            lines.append(OcrLine(text=text, confidence=float(score), bbox=_to_bbox(points)))
        return lines


_ENGINES: Dict[str, OcrEngine] = {}


def get_engine(name: Optional[str] = None) -> OcrEngine:
    """Return a cached engine instance. Unknown names fail with a clear error."""
    chosen = (name or os.environ.get("OCR_ENGINE") or "rapidocr").strip().lower()
    if chosen == "rapidocr":
        engine = _ENGINES.get(chosen)
        if engine is None:
            engine = RapidOcrEngine()
            _ENGINES[chosen] = engine
        return engine
    raise ValueError(f"Unknown OCR engine '{chosen}'. Available: rapidocr")


def engine_available(name: str = "rapidocr") -> bool:
    if name != "rapidocr":
        return False
    try:
        import rapidocr_onnxruntime  # noqa: F401

        return True
    except Exception:  # pragma: no cover - environment without the extra
        return False


def ocr_image(
    image: Any,
    engine: Optional[str] = None,
) -> OcrResult:
    """Run OCR on a bytes/numpy/PIL image. Returns a provenance-carrying result."""
    from PIL import Image  # local import keeps the runtime lean without OCR deps

    if isinstance(image, (bytes, bytearray)):
        import io

        array = np.array(Image.open(io.BytesIO(image)).convert("RGB"))
    elif isinstance(image, Image.Image):
        array = np.array(image.convert("RGB"))
    else:
        array = np.asarray(image)
        if array.ndim == 2:
            array = np.stack([array] * 3, axis=-1)

    height, width = int(array.shape[0]), int(array.shape[1])
    started = time.time()
    lines = get_engine(engine).recognize(array)
    duration_ms = int((time.time() - started) * 1000)
    mean_confidence = (
        round(float(np.mean([line.confidence for line in lines])), 4) if lines else 0.0
    )
    return OcrResult(
        lines=tuple(lines),
        engine=engine or os.environ.get("OCR_ENGINE", "rapidocr"),
        duration_ms=duration_ms,
        mean_confidence=mean_confidence,
        width=width,
        height=height,
    )


def _median(values: Sequence[float], default: float = 1.0) -> float:
    cleaned = [v for v in values if v > 0]
    if not cleaned:
        return default
    ordered = sorted(cleaned)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


@dataclass(frozen=True)
class CellRow:
    cells: Tuple[str, ...]
    y: float


def lines_to_rows(lines: Sequence[OcrLine], y_tolerance: Optional[float] = None) -> List[CellRow]:
    """
    Reconstruct a simple grid deterministically from OCR boxes.

    Rows are y-clusters; columns are split where the horizontal gap is large
    relative to the median box height. It is deliberately conservative: when
    the grid cannot be inferred, cells collapse into a single column rather
    than being invented.
    """
    usable = [line for line in lines if line.text]
    if not usable:
        return []

    heights = [line.bbox[3] - line.bbox[1] for line in usable]
    tol = y_tolerance if y_tolerance is not None else _median(heights) * 0.6
    gap_threshold = _median(heights) * 1.8

    ordered = sorted(usable, key=lambda line: (line.bbox[1], line.bbox[0]))
    rows: List[List[OcrLine]] = []
    for line in ordered:
        if rows and abs(line.bbox[1] - rows[-1][0].bbox[1]) <= tol:
            rows[-1].append(line)
        else:
            rows.append([line])

    result: List[CellRow] = []
    for row in rows:
        row.sort(key=lambda line: line.bbox[0])
        cells: List[str] = []
        current = row[0].text
        previous_right = row[0].bbox[2]
        for line in row[1:]:
            if line.bbox[0] - previous_right > gap_threshold:
                cells.append(current.strip())
                current = line.text
            else:
                current += " " + line.text
            previous_right = max(previous_right, line.bbox[2])
        cells.append(current.strip())
        y = float(np.mean([line.bbox[1] for line in row]))
        result.append(CellRow(cells=tuple(c for c in cells if c), y=y))
    return result


def rows_to_records(rows: Sequence[CellRow]) -> List[Dict[str, Any]]:
    """Interpret the first non-empty row as a header and build records."""
    non_empty = [row for row in rows if row.cells]
    if len(non_empty) < 2:
        return []
    header = [str(cell).strip() or f"column_{i + 1}" for i, cell in enumerate(non_empty[0].cells)]
    records: List[Dict[str, Any]] = []
    for row in non_empty[1:]:
        record: Dict[str, Any] = {}
        for index, key in enumerate(header):
            record[key] = row.cells[index] if index < len(row.cells) else ""
        records.append(record)
    return records
