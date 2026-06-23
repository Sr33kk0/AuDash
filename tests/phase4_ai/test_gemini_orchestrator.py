import pytest

from ai.gemini_orchestrator import build_sentiment_prompt


def test_prompt_includes_headlines_and_metrics():
    prompt = build_sentiment_prompt(
        [{"title": "Fed holds rates", "link": "u1"},
         {"title": "Inflation cools", "link": "u2"}],
        {"gold_silver_ratio": 80.5},
    )
    assert "Fed holds rates" in prompt
    assert "Inflation cools" in prompt
    assert "gold_silver_ratio" in prompt
    assert "80.5" in prompt


def test_prompt_states_scale_and_json_keys():
    prompt = build_sentiment_prompt([], {})
    assert "-5" in prompt and "5" in prompt
    assert "sentiment_score" in prompt
    assert "dominant_risk_factor" in prompt
    assert "analytical_summary" in prompt
    assert "JSON" in prompt


def test_prompt_handles_empty_inputs():
    prompt = build_sentiment_prompt([], {})
    assert "no recent macroeconomic headlines" in prompt
    assert "no market metrics provided" in prompt
