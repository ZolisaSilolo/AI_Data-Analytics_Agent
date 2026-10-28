# Determinism contract

Status: implemented (Phase 2 core, October 2026)
Owner: backend

## The problem

Arithmetic determinism was already solved — every number a user sees comes from
DuckDB/Polars/NumPy, never from model text. What remained stochastic:

* **Semantics** — "revenue", "NRR", "churn" were re-derived as SQL on every run.
* **Schema** — the planner discovered columns by trial and error, wasting its
  5-round budget and guessing at dtypes.
* **Evidence** — the narrative was returned unverified; a number could appear in
  prose that no tool produced.
* **Statistics** — several discipline tools overstated their rigour (hard-coded
  reconciliation, unlabelled single-touch attribution, Wald-only intervals).

## The five levels

| Level | Property | Mechanism |
|---|---|---|
| L0 Arithmetic | Same inputs ⇒ same numbers | Locked DuckDB, typed tools, pinned results |
| L1 Logical | Same question ⇒ same plan, same formula | Metric catalogue + typed plan (Analyst IR) |
| L2 Statistical | Same estimator, stated assumptions | Method contracts (assumptions, CI method, alpha) |
| L3 Evidential | Every claim traceable to a computed value | Claim verifier (prose ↔ facts) |
| L4 Operational | Same job ⇒ replayable artifact | Plan hash + versions (planned) |

## Implemented controls

### 1. Metric catalogue — `src/semantic/`

Metrics are defined once in `catalog.json` (name, version, unit, formula,
required columns, aliases) and compiled to SQL by `src/semantic/catalog.py`.
Binding resolves columns deterministically: exact match, then normalised match,
then declared alias. Ambiguity makes the metric **unavailable**, never guessed.
Derived metrics (e.g. `aov = revenue / order_count`) expand recursively.

The model calls `query_metric(metric, group_by, filters, order, limit)` for any
catalogued metric. The formula cannot drift between runs. When no metric fits,
the system must say so rather than invent one ("refuse rather than guess").

### 2. Typed analysis plan — `src/plan/`

`AnalysisPlan` is a closed-schema object (`intent`, `metrics`, `group_by`,
typed `filters`, `time_column`/`grain`, `limit`, `order`, `acceptance`).
Unknown keys are rejected — a plan must not smuggle unchecked semantics past
the hash. `plan_hash()` (SHA-256 of the canonical JSON) is the replay key.
`src/plan/compiler.py` compiles `aggregate` and `trend` plans to one guarded
SQL statement; every identifier is validated against the dataset schema and
quoted, every literal escaped.

### 3. Schema card — `src/dataprof/schema_card.py`

A deterministic profile (per column: dtype, inferred role, null rate,
distinct count, range/mean or top values) is injected into the system prompt
before planning. It is token-bounded and contains no row-level payload. This
removed the planner's need to burn a round on `SELECT * LIMIT 5`.

### 4. Claim verifier — `src/verify/claims.py`

Every number in the narrative is extracted (thousands separators, decimals,
percent signs, k/M/B suffixes) and matched against the numbers tools actually
produced, within a 0.5% tolerance and with rounding awareness. Percent claims
match the corresponding fraction fact. Calendar years that are not facts are
ignored. The result rides on the job as `verification`
(`PASS` / `REVIEW` / `NO_CLAIMS`) and the frontend shows it. Fail closed:
unsupported *critical* numbers are flagged, never silently kept.

### 5. Discipline corrections — `src/disciplines/`

* Funnels are sequential (AND across steps, or first-occurrence ordered per
  user); step conversion can no longer exceed 100%.
* Attribution computes real first/last/linear/position-based shares **only**
  when a user key and timestamp exist; otherwise it is labelled
  `single_touch_channel_share`.
* The ARR waterfall runs its identity through the invariant checker and can
  reconcile against an externally stated ending ARR.
* The runway simulation uses a local seeded `Generator`, records seed,
  distribution and assumptions, and offers a lognormal option.
* Clinical uses Haldane-Anscombe for zero cells, reports the CI method,
  relative risk interval, sample size and assumptions.

## Verification of the verification

The new controls are covered by 62 additional tests (150 total):

* catalogue loading, binding (exact/alias/ambiguous/unavailable), bounded prompt
* compiled SQL runs in the sandbox and returns the expected aggregates
* plan parsing/hashing/compilation; injected literals stay quoted
* profile determinism and role inference
* claim extraction/matching across formats; zero-fact behaviour
* funnel ordering, retention completeness, attribution shares, seeded runway

## What is deliberately not done yet

* The plan IR is validated and compilable but not yet emitted by the model —
  that arrives with the Strands migration (`structured_output_model`), where
  schema violations retry automatically.
* L4 replay storage (persisting `dataset_sha · plan_hash · engine_version ·
  seed`) is designed, not yet persisted.
* Narrative rewriting on verification failure: today we flag, we do not rewrite.
