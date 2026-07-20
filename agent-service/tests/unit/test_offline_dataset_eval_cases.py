"""Contract tests for the sanitized offline dataset evaluation fixture.

The fixture is intentionally test-only. It is not a runtime data source, not
RAG, not retrieval, and not a source of quotation truth. These tests only keep
the offline evaluation artifact aligned with the current typed contracts and
privacy posture.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.agent.orchestrator import _looks_like_a_price_mention
from app.agent.policies.handoff_policy import detect_human_request_keywords
from app.agent.tools import parse_get_quote_args, parse_record_lead_info_args

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "offline_dataset_eval_cases.json"

REQUIRED_CATEGORIES = {
    "informal_greeting",
    "vehicle_year_extraction",
    "ambiguous_vehicle_description",
    "multi_field_message",
    "missing_vehicle_year",
    "missing_age",
    "missing_plan",
    "soft_missing_cep",
    "volunteered_pii_redaction",
    "media_or_attachment",
    "objection_price",
    "objection_competitor",
    "objection_franchise",
    "positive_acceptance",
    "explicit_human_request",
    "out_of_scope",
    "business_refusal_age",
    "business_refusal_vehicle_age",
    "price_fabrication_guard",
    "user_correction_coverage_gap",
}

RAW_PII_PATTERNS = {
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "phone": re.compile(r"\b(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b"),
    "plate": re.compile(r"\b[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}\b"),
    "cep": re.compile(r"\b\d{5}-?\d{3}\b"),
}


def _load_cases() -> list[dict[str, Any]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_walk_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(_walk_strings(item))
        return strings
    return []


def test_fixture_is_small_and_covers_required_offline_eval_categories():
    cases = _load_cases()

    assert 20 <= len(cases) <= 30
    assert {case["category"] for case in cases} >= REQUIRED_CATEGORIES


def test_fixture_contains_no_raw_pii_shaped_values():
    cases = _load_cases()
    all_text = "\n".join(string for case in cases for string in _walk_strings(case))

    for label, pattern in RAW_PII_PATTERNS.items():
        assert not pattern.search(all_text), f"Fixture contains raw {label}-shaped text"


def test_expected_record_lead_info_payloads_parse_against_current_tool_contract():
    for case in _load_cases():
        payload = case.get("expected_record_lead_info", {})
        args = parse_record_lead_info_args(payload)
        assert args is not None


def test_expected_get_quote_payloads_parse_against_current_tool_contract():
    for case in _load_cases():
        payload = case.get("expected_get_quote")
        if payload is None:
            continue
        args = parse_get_quote_args(payload)
        assert args is not None


def test_fixture_handoff_keyword_cases_match_deterministic_policy():
    for case in _load_cases():
        if not case.get("expect_handoff_keyword"):
            continue
        assert detect_human_request_keywords(case["lead_message"]) is True


def test_fixture_price_guard_cases_match_plain_text_guard():
    for case in _load_cases():
        if not case.get("expect_price_guard"):
            continue
        candidate = case["llm_plain_text_candidate"]
        assert _looks_like_a_price_mention(candidate) is True
