# OmniAnalyst — The Determinism Contract (Mermaid)

```mermaid
flowchart LR
    Q[Question] --> P[Planner: Bedrock model]
    SC[Schema Card] -.-> P
    P --> IR[Typed Plan: AnalysisPlan v1 + plan_hash]
    MC[Metric Catalogue] -.-> CP
    IR --> CP[Compiler: guarded SQL]
    CP --> EX[Executor: DuckDB / methods]
    EX --> VR[Verifier: claims vs facts]
    VR --> NR[Narrator: facts only]
    NR --> R[Report + badge]
    GS[Golden Set] -.-> CI[CI gate]
    RT[Replay Tuple] -.-> EX
```

## The five rules

1. The planner never computes: every number comes from the executor.
2. The plan is a typed, hashed object; unknown keys are rejected.
3. Catalogued metrics compile to one versioned formula.
4. The narrator sees facts, not data; unsupported numbers are flagged.
5. Same dataset + same plan hash + same engine = same result.
