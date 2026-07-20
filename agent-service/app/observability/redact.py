"""Scrubs incidental PII (CPF, phone, email, plate) from free text before it
reaches logs or a handoff summary. redact_pii does not touch the
legitimately-collected business fields (idade, veiculo_ano, cep) — those
are intended qualification data, not leakage. CEP is the one exception
worth a dedicated helper: it's precise enough to identify an address, so
call sites that expose it for observability or hand it to a human operator
(logs, handoff_policy.render_summary()) truncate it to its 2-digit region
prefix via redact_cep — the full value stays in operational state
(LeadProfile, the quote request), where it's legitimately needed.
"""
from __future__ import annotations

import re

_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_PHONE_RE = re.compile(r"\b(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PLATE_RE = re.compile(r"\b[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}\b")

_PATTERNS = (
    (_CPF_RE, "[cpf]"),
    (_EMAIL_RE, "[email]"),
    (_PLATE_RE, "[placa]"),
    (_PHONE_RE, "[telefone]"),
)


def redact_pii(text: str) -> str:
    redacted = text
    for pattern, placeholder in _PATTERNS:
        redacted = pattern.sub(placeholder, redacted)
    return redacted


def redact_cep(cep: str | None) -> str | None:
    """Truncates a CEP to its 2-digit prefix — the only part relevant to
    region-risk observability; the full value isn't needed in logs."""
    if not cep:
        return cep
    digits = cep.replace("-", "").strip()
    return digits[:2] if digits else cep
