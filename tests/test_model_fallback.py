"""Model-selection behaviour: failover is opt-in, and capabilities are probed."""

from __future__ import annotations

import pytest
from botocore.exceptions import ClientError

from agent.bedrock_core import BedrockAgentCore

PRIMARY = "global.moonshotai.kimi-k3"
SECONDARY = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"


class FakeBedrock:
    """Minimal Converse stand-in that records calls and inference configs."""

    def __init__(
        self,
        failures: dict[str, str] | None = None,
        reject_temperature: tuple[str, ...] = (),
    ) -> None:
        self.calls: list[str] = []
        self.inference_configs: list[dict] = []
        self.failures = failures or {}
        self.reject_temperature = set(reject_temperature)

    def converse(self, **kwargs):
        model_id = kwargs["modelId"]
        self.calls.append(model_id)
        inference = dict(kwargs.get("inferenceConfig") or {})
        self.inference_configs.append(inference)

        if model_id in self.reject_temperature and "temperature" in inference:
            raise ClientError(
                {
                    "Error": {
                        "Code": "ValidationException",
                        "Message": "This model doesn't support the temperature field.",
                    }
                },
                "Converse",
            )

        code = self.failures.get(model_id)
        if code:
            raise ClientError({"Error": {"Code": code, "Message": code}}, "Converse")

        return {
            "output": {"message": {"role": "assistant", "content": [{"text": "done"}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 3, "outputTokens": 2, "totalTokens": 5},
        }


def build(fake: FakeBedrock, **kwargs) -> BedrockAgentCore:
    agent = BedrockAgentCore(sandbox=object(), **kwargs)
    agent.client = fake
    return agent


def test_empty_fallback_is_disabled_and_does_not_switch(monkeypatch):
    monkeypatch.setenv("BEDROCK_FALLBACK_MODEL", "")
    agent = build(FakeBedrock({PRIMARY: "AccessDeniedException"}), primary_model=PRIMARY)
    assert agent.fallback_model is None

    with pytest.raises(ClientError):
        agent.run_conversation("How many rows?")

    assert agent.client.calls == [PRIMARY]


def test_configured_fallback_is_used_on_access_denied():
    fake = FakeBedrock({PRIMARY: "AccessDeniedException"})
    agent = build(fake, primary_model=PRIMARY, fallback_model=SECONDARY)

    result = agent.run_conversation("How many rows?")

    assert result["status"] == "SUCCESS"
    assert result["model_used"] == SECONDARY
    assert fake.calls == [PRIMARY, SECONDARY]
    assert result["usage"]["total_tokens"] == 5


def test_throttling_is_not_masked_by_failover():
    fake = FakeBedrock({PRIMARY: "ThrottlingException"})
    agent = build(fake, primary_model=PRIMARY, fallback_model=SECONDARY)

    with pytest.raises(ClientError):
        agent.run_conversation("How many rows?")

    assert fake.calls == [PRIMARY]


def test_temperature_is_dropped_when_the_model_rejects_it():
    """Kimi K3 rejects `temperature`; the same model must be retried without it."""
    fake = FakeBedrock(reject_temperature=(PRIMARY,))
    agent = build(fake, primary_model=PRIMARY)

    result = agent.run_conversation("How many rows?")

    assert result["status"] == "SUCCESS"
    assert fake.calls == [PRIMARY, PRIMARY]
    assert "temperature" in fake.inference_configs[0]
    assert "temperature" not in fake.inference_configs[1]
    assert PRIMARY in agent._rejects_temperature


def test_temperature_probe_is_cached_between_runs():
    fake = FakeBedrock(reject_temperature=(PRIMARY,))
    agent = build(fake, primary_model=PRIMARY)

    agent.run_conversation("first")
    agent.run_conversation("second")

    # One rejected probe, then two clean calls.
    assert fake.calls == [PRIMARY, PRIMARY, PRIMARY]
    assert all("temperature" not in cfg for cfg in fake.inference_configs[1:])
