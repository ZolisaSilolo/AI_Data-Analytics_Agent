#!/usr/bin/env python
"""
Preflight Bedrock model access.

Fails fast and loudly when the configured primary/fallback model or inference
profile is not enabled for this account/region. Run before ``sam deploy``.

Usage:
    BEDROCK_PRIMARY_MODEL=global.moonshotai.kimi-k3 \
    python scripts/verify_bedrock_access.py [--region us-east-1]

An empty BEDROCK_FALLBACK_MODEL disables failover and is reported as SKIP.
"""

from __future__ import annotations

import argparse
import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

PRIMARY = os.environ.get("BEDROCK_PRIMARY_MODEL", "global.moonshotai.kimi-k3")
FALLBACK = (os.environ.get("BEDROCK_FALLBACK_MODEL", "") or "").strip()


def check(client, model_id: str) -> bool:
    """
    Send a 1-token Converse request.

    ``temperature`` is retried away when a model rejects sampling parameters, so
    the preflight matches what the worker does at runtime instead of failing on
    a capability the app already adapts to.
    """
    attempts = ({"maxTokens": 32, "temperature": 0}, {"maxTokens": 32})
    for index, inference in enumerate(attempts):
        try:
            response = client.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": "Reply with OK."}]}],
                inferenceConfig=inference,
            )
            text = "".join(
                block.get("text", "")
                for block in response.get("output", {}).get("message", {}).get("content", [])
            )
            note = "" if index == 0 else "  [no temperature: model rejects it]"
            print(f"  OK   {model_id} -> {text.strip()[:40]!r}{note}")
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            message = exc.response.get("Error", {}).get("Message", "")
            retry_without_temperature = (
                index == 0
                and code == "ValidationException"
                and "temperature" in message.lower()
            )
            if retry_without_temperature:
                continue
            print(f"  FAIL {model_id} -> {code}: {message}", file=sys.stderr)
            if code in {"AccessDeniedException", "ResourceNotFoundException"}:
                print(
                    "       Grant model access in the Bedrock console for this account/region, "
                    "and use a cross-region inference profile id where required.",
                    file=sys.stderr,
                )
            elif code == "ValidationException":
                print(
                    "       The model rejected this request as configured: check the model id, "
                    "whether it requires an inference profile, and its supported parameters.",
                    file=sys.stderr,
                )
            return False
        except BotoCoreError as exc:
            print(f"  FAIL {model_id} -> {exc}", file=sys.stderr)
            return False
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default=None, help="Defaults to your AWS config/boto session")
    args = parser.parse_args()

    session = boto3.Session()
    region = args.region or session.region_name or "us-east-1"
    client = session.client("bedrock-runtime", region_name=region)
    print(f"Verifying Bedrock access in {region}:")
    primary_ok = check(client, PRIMARY)

    fallback_ok = True
    if FALLBACK:
        fallback_ok = check(client, FALLBACK)
    else:
        print("  SKIP no fallback configured; failover is disabled")

    if not primary_ok:
        print("\nPrimary model is not usable. Do not deploy.", file=sys.stderr)
        return 2
    if not fallback_ok:
        print("\nPrimary works but fallback does not; failover will be unavailable.", file=sys.stderr)
        return 1
    print("\nAll configured models are reachable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
