#!/usr/bin/env python
"""
Seed the lakehouse with a deterministic sample dataset.

Writes CSV and Parquet to ``uploads/<tenant>/<uuid>.{csv,parquet}`` so the keys
pass the same validation used by the API. Idempotent: the key is derived from a
stable UUID, so re-running overwrites the same two objects.

Usage:
    python scripts/seed_sample_data.py --bucket <bucket> --tenant public
"""

from __future__ import annotations

import argparse
import io
import sys
import uuid

import boto3
import numpy as np
import pandas as pd

SEED_NAMESPACE = uuid.UUID("6f1c2f1a-3f6a-5c2f-9a1e-6c6f7d2b8a10")


def build_frame(rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2024-01-01")
    dates = [start + pd.Timedelta(days=int(d)) for d in rng.integers(0, 365, rows)]

    signup = np.ones(rows, dtype=int)
    onboarded = (rng.random(rows) < 0.72).astype(int)
    paid = ((onboarded == 1) & (rng.random(rows) < 0.42)).astype(int)

    channels = rng.choice(["organic", "paid_search", "social", "referral"], rows)
    revenue = np.round(rng.gamma(shape=2.0, scale=180.0, size=rows) * paid, 2)
    lead_time = np.round(np.abs(rng.normal(36, 12, rows)), 2)
    exposed = (channels == "paid_search").astype(int)
    cases = ((exposed == 1) & (rng.random(rows) < 0.28)).astype(int)

    return pd.DataFrame(
        {
            "event_date": [d.strftime("%Y-%m-%d") for d in dates],
            "user_id": [f"u{i:05d}" for i in range(rows)],
            "cohort_month": [d.strftime("%Y-%m") for d in dates],
            "period_index": rng.integers(0, 6, rows),
            "signup": signup,
            "onboarded": onboarded,
            "paid": paid,
            "channel": channels,
            "conversions": paid,
            "spend": np.round(rng.uniform(5, 60, rows), 2),
            "revenue": revenue,
            "lead_time_hours": lead_time,
            "exposed": exposed,
            "cases": cases,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the OmniAnalyst lakehouse.")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--tenant", default="public")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--region", default=None)
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    s3 = session.client("s3")
    df = build_frame(rows=args.rows)

    dataset_id = uuid.uuid5(SEED_NAMESPACE, f"sample/{args.tenant}/{args.rows}")
    csv_key = f"uploads/{args.tenant}/{dataset_id}.csv"
    parquet_key = f"uploads/{args.tenant}/{dataset_id}.parquet"

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(
        Bucket=args.bucket,
        Key=csv_key,
        Body=csv_buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
        ServerSideEncryption="AES256",
    )

    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False)
    s3.put_object(
        Bucket=args.bucket,
        Key=parquet_key,
        Body=parquet_buffer.getvalue(),
        ContentType="application/vnd.apache.parquet",
        ServerSideEncryption="AES256",
    )

    print(f"Seeded {len(df)} rows")
    print(f"  CSV:     s3://{args.bucket}/{csv_key}")
    print(f"  Parquet: s3://{args.bucket}/{parquet_key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
