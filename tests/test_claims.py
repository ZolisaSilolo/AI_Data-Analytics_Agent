"""Claim verification: prose numbers versus tool-produced numbers."""

from __future__ import annotations

from verify import collect_facts, extract_numbers, verify_claims


def test_extract_numbers_formats():
    text = "Revenue was 4,500.5 in AMER, up 12.5%, spend $1.2M, 3k users, model Kimi K3, year 2024."
    claims = extract_numbers(text)
    values = [c.value for c in claims]
    assert 4500.5 in values
    assert any(c.is_percent and c.value == 12.5 for c in claims)
    assert 1_200_000.0 in values
    assert 3_000.0 in values
    assert all("K3" not in c.raw for c in claims)


def test_supported_numbers_pass():
    narrative = "Total revenue was 4500 and the top region converted at 12.5%."
    facts = [4500.0, 0.125]
    result = verify_claims(narrative, facts)
    assert result["status"] == "PASS"
    assert result["supported"] == 2
    assert result["unsupported_count"] == 0


def test_unsupported_number_is_flagged():
    narrative = "Total revenue was 9000."
    result = verify_claims(narrative, [4500.0])
    assert result["status"] == "REVIEW"
    assert result["unsupported"][0]["value"] == 9000.0
    assert result["unsupported"][0]["severity"] == "critical"


def test_percent_matches_a_fraction_fact():
    result = verify_claims("Conversion reached 25%.", [0.25])
    assert result["status"] == "PASS"


def test_rounded_claim_is_accepted():
    result = verify_claims("Revenue was about 4.5k.", [4499.6])
    assert result["status"] == "PASS"


def test_years_are_ignored_when_not_facts():
    result = verify_claims("In 2024 revenue was 4500.", [4500.0])
    assert result["status"] == "PASS"
    assert result["ignored_years"] == 1


def test_no_numbers_is_no_claims():
    result = verify_claims("The analysis failed to produce a result.", [1.0])
    assert result["status"] == "NO_CLAIMS"


def test_collect_facts_walks_nested_payloads():
    payload = {
        "row_count": 6,
        "data": [{"revenue": 100.5, "region": "AMER"}, {"revenue": 200.25}],
        "invariants": {"checks": [{"sample_size": 6}]},
        "note": "not numeric",
        "skip": None,
        "flag": True,
    }
    facts = collect_facts(payload)
    assert 6.0 in facts
    assert 100.5 in facts
    assert 200.25 in facts
    assert True not in facts
