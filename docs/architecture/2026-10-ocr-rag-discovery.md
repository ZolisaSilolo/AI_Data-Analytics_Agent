# Discovery: lightweight OCR + semantic RAG (S3 Vectors)

Status: decided (October 2026). Modules implemented: `src/ingest/`, `src/rag/`.
Deployment wiring is Phase 5; this document records the research that drove it.

## Requirements

1. Cheap and lightweight — no GPU, no heavy container, Lambda-viable.
2. Open-source only for OCR (the LLM stays on open-weight Bedrock models per
   the model decision; embeddings may be any Bedrock model).
3. Complements RAG: OCR produces *evidence for retrieval*; the numbers still
   go through the deterministic engine, never through a vector.
4. Tables matter more than glyphs for an analyst.

## OCR landscape (sources checked 2026-10)

| Engine | Size/compute | Strengths | Verdict |
|---|---|---|---|
| **RapidOCR** (PP-OCRv5, ONNX Runtime) | ~15 MB, CPU-only, no PyTorch | Fast text lines, multilingual, offline | **Default** — already installed, 5.7 s cold start measured here |
| **Docling** (IBM, MIT) | Heavier (layout + TableFormer) | Best open layout/table structure pipeline; RapidOCR is a supported backend | Phase 5 upgrade tier for complex tables |
| **Tesseract** | ~10 MB binary, CPU | Ubiquitous, 100+ languages | Lower accuracy on business docs; not chosen |
| **Surya 2** | VLM < 3B, CPU-possible/GPU-preferred | Best small-VLM doc parser (86.6 tables on olmOCR-bench) | Too heavy for the cheap tier |
| **dots.ocr / dots.mocr** | 3B VLM, GPU | SOTA OmniDocBench (88.4) | Server-tier only |
| **PaddleOCR-VL** | 0.9B VLM | Strong, still GPU-ish | Watch |

Key insight repeated across benchmarks (Newtuple 2026, Docling guides,
CodeSOTA 2026): **no single engine wins across document types**, and on tables
the bottleneck is *structure*, not glyph recognition. Hence a tiered design.

## Decision: the OCR pipeline (`src/ingest/`)

```
document ──► digital? (PDF text layer via pypdf) ──► use it (free, exact)
           └─ scanned? ──► render (pypdfium2, 2× scale) ──► RapidOCR (CPU)
                                          │
                          lines_to_rows → rows_to_records → candidate tables
                                          │
                              chunk_text → semantic index (RAG)
```

* `ocr.py` — engine protocol + RapidOCR (lazy singleton), box → line model.
* `documents.py` — one entry point `extract_document(bytes, filename)` for
  PDF/PNG/JPG/TIFF/CSV/Parquet/XLSX/TXT; reports `method`
  (`text_layer` | `ocr` | `table` | `text`) plus per-page engine provenance.
* `chunking.py` — deterministic word-boundary chunks (same input ⇒ same
  chunks ⇒ stable embeddings).
* Table reconstruction is deliberately conservative: rows are y-clusters,
  columns split on large x-gaps. When the grid is unclear, cells collapse into
  one column rather than being invented.

OCR output is **evidence for ingestion and retrieval**, never a source of
numbers for the narrative. A table that comes from OCR is re-registered as a
dataset and analysed by the engine like any upload.

## Decision: semantic RAG on S3 Vectors (`src/rag/`)

Store choice, from AWS docs (us-east-1, verified 2026-10):

* 2B vectors per index, dimensions 1–4096, up to 500 vectors per `PutVectors`,
  `topK` up to 10,000, ~100 ms warm queries, pay-per-query, up to 90% cheaper
  than specialised vector databases.
* Semantic only (no hybrid) when fronted by Bedrock Knowledge Bases; 1 KB
  custom metadata / 35 keys per vector in that integration; this module keeps
  filterable metadata under that budget.
* Titan Text Embeddings V2 at **512 dimensions** retains ~99% of the 1024-dim
  accuracy at half the storage (AWS, 2024) — the default here.

What lives in the index (and what never does):

| Content | Indexed | Why |
|---|---|---|
| Metric definitions (`catalog_as_documents`) | ✅ | Grounds the planner; same formula every time |
| Data dictionary / business glossary | ✅ | Terminology retrieval |
| Prior analysis summaries + plan hashes | ✅ | Reuse, audit trail |
| Extracted document text (OCR/text layer) | ✅ | Search over uploaded reports |
| Raw data rows / computed numbers | ❌ | Retrieval is approximate; numbers come from the engine |

`SemanticIndex` is tenant-scoped (`tenant_id` is a mandatory metadata filter
on every query), so retrieval obeys the same isolation as the lakehouse once
Phase 1 auth lands.

## How OCR complements RAG

OCR is the *intake multiplier* for RAG: it turns invoices, statements, and
scanned reports into (a) searchable chunks and (b) candidate tables. RAG is the
*meaning layer* for OCR: a question like "what does 'net revenue' mean here?"
is answered from definitions, not guessed. The two meet only at ingestion —
never at computation. That boundary is the same one the whole platform holds:
**retrieval for meaning, engines for measurement.**

## Cost shape (list prices, verify before budgeting)

* RapidOCR: free, CPU; ~5.7 s cold start, ~1–2 s/page warm on Graviton.
* Titan Embed V2: per-token embedding; a 100-page report ≈ 30–60k tokens ≈ cents.
* S3 Vectors: pay-per-vector stored + pay-per-query; negligible at this scale
  versus model inference.
* The dominant cost of an analysis remains LLM tokens; OCR+RAG add ~1–2%.

## Deferred alternatives

* **Bedrock Data Automation** — managed, higher accuracy with confidence
  scores and bounding boxes. Kept as the enterprise tier; costs per page.
* **KB structured data (NL→SQL over Redshift/Glue)** — only applies once data
  lives in Redshift/Glue, not per-request CSVs.
* **VLM OCR tier (Surya 2 / dots.ocr)** — revisit when GPU capacity exists.
