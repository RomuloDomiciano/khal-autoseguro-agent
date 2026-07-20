# Dataset Analysis

This report treats `dataset/conversations.parquet` as an offline engineering
and evaluation artifact for the AutoSeguro agent. It is not used as a runtime
source of truth, prompt store, retrieval index, RAG corpus, embedding source, or
vector database input.

The quote-service remains the only source of truth for price and eligibility.
The agent-service remains responsible for state, validation, retries, handoff,
and deterministic quote rendering.

## Sanitization

The dataset is synthetic, but its content intentionally contains plausible
personal-data formats. This report uses aggregate counts and sanitized examples
only. Raw names, CPF-like values, phone-like values, email-like values,
plate-like values, and exact customer-looking address data are not copied here.

Representative fixtures use placeholders such as `[cpf]`, `[email]`,
`[telefone]`, `[placa]`, and `[cep]`.

## Schema

Each parquet row is one message. A conversation is reconstructed by grouping on
`conversation_id` and sorting by `message_index`.

| Column | Type | Notes |
|---|---|---|
| `conversation_id` | string | Conversation identifier. |
| `message_index` | int | Message order within the conversation. |
| `timestamp` | string | ISO-style timestamp. |
| `sender_role` | string | `lead` or `vendedor`. |
| `sender_name` | string | Display name; treated as sensitive. |
| `message_type` | string | `text`, `image`, `audio`, or `document`. |
| `message_body` | string | Free text, or a media marker for non-text messages. |
| `channel` | string | Always `whatsapp`. |
| `conversation_outcome` | string | `ganho`, `perdido`, `em_negociacao`, or `sem_resposta`. |
| `lead_idade_informada` | int | Reported age when applicable. |
| `veiculo_texto` | string | Free-form vehicle description. |

## Aggregate Shape

Parquet inspection found:

| Metric | Count |
|---|---:|
| Conversations | 2,500 |
| Messages | 26,470 |
| Lead messages | 16,470 |
| Seller messages | 10,000 |
| Text messages | 24,681 |
| Document markers | 774 |
| Image markers | 550 |
| Audio markers | 465 |

Conversation outcomes:

| Outcome | Conversations |
|---|---:|
| `em_negociacao` | 757 |
| `ganho` | 712 |
| `perdido` | 538 |
| `sem_resposta` | 493 |

Messages per conversation:

| Metric | Value |
|---|---:|
| Min | 8 |
| Median | 11 |
| P90 | 12 |
| Max | 14 |

## Patterns Relevant To The Agent

### Informal Portuguese

The dataset contains informal WhatsApp-style Portuguese: short greetings,
contracted wording, acceptance phrases, conversational shorthand, and terse
follow-ups. Aggregate matching found 3,373 lead text messages with informal
markers.

Evaluation implication: the agent should tolerate informal phrasing and should
respond in concise Brazilian Portuguese rather than formal support-script prose.

### Incomplete Information

Lead messages often provide only one piece of quote-relevant information at a
time. Aggregate quote-field detection in lead text messages found:

| Detected quote-related fields in one message | Messages |
|---|---:|
| 0 | 8,302 |
| 1 | 3,844 |
| 2 | 2,535 |
| 3+ | 0 |

Evaluation implication: the agent must keep explicit conversation state and ask
for only the missing fields instead of restarting the qualification flow.

### Multiple Fields In One Message

The dataset also has a highly recurring multi-field pattern: a single lead
message often contains age, location-like data, and CPF-like text together.
There are 2,500 such messages.

Evaluation implication: tool-calling extraction should support partial and
multi-field updates in one turn, and should ignore volunteered fields that are
not needed for quoting.

### Volunteered PII

Sensitive-looking data is common:

| Pattern | Lead text messages |
|---|---:|
| CPF-shaped text | 2,500 |
| Email-shaped text | 1,379 |
| Phone-shaped text | 1,379 |
| Plate-shaped text | 839 |

Evaluation implication: the agent should minimize what it extracts, avoid
logging raw message bodies, redact handoff summaries, and never put raw
PII-shaped values into documentation or fixtures.

### Ambiguous Vehicle Descriptions

Vehicle information is free-form. All conversations contain a vehicle year in
some form, but the wording varies. Aggregate style checks found 861 messages
using an `ano` style and 831 using an "e/é um ..." style.

Evaluation implication: natural-language extraction should handle vehicle
descriptions such as "modelo, ano 2022" and "é um hatch 2020", while the
backend should still validate the final typed `veiculo_ano`.

### Objections And Negotiation

Objection language appears frequently: price, franchise, competitor, and
"need to think" patterns occur in 1,295 lead text messages.

Evaluation implication: after a quote is resolved, follow-up conversation
should remain conversational, but the agent must not invent discounts,
alternative prices, or pricing explanations outside the quote-service result.

### Human Support Requests

The dataset does not materially contain explicit requests matching the current
handoff policy keywords such as "atendente", "humano", "pessoa de verdade",
"falar com alguém", or "supervisor". Some messages contain contact-continuation
language, but that is not the same as asking for human handoff.

Evaluation implication: explicit human handoff should remain in the evaluation
fixture because it is required by the challenge, but this dataset should not be
over-claimed as evidence for that behavior.

### User Corrections

Correction markers such as "na verdade", "corrigindo", "ops", "quer dizer",
and similar phrases were not found in the dataset.

Evaluation implication: user correction is a known evaluation gap. It is useful
to include a small synthetic correction case in deterministic eval fixtures,
but it should be documented as challenge-relevant coverage rather than a
recurring dataset pattern.

### Media Markers

Lead messages include 1,789 non-text media markers across document, image, and
audio types. There are no transcripts for media.

Evaluation implication: the backend should not pretend to understand media
content. The current architecture can safely hand off unsupported media without
adding OCR, speech-to-text, RAG, or new infrastructure.

## Evaluation Fixture Strategy

The deterministic fixture at
`agent-service/tests/fixtures/offline_dataset_eval_cases.json` is intentionally
small: about two dozen representative, sanitized cases. It is handcrafted from
aggregate dataset patterns rather than copied from raw records.

The fixture covers:

- informal Portuguese
- vehicle-year extraction
- ambiguous vehicle descriptions
- multiple fields in one message
- missing required fields
- soft missing CEP
- volunteered PII placeholders
- media markers
- objections
- positive acceptance
- explicit human request
- out-of-scope request
- quote-service business refusal inputs
- price-fabrication guard examples
- user correction as a documented coverage gap

The focused tests load this fixture only in the test suite. They validate that
the cases stay sanitized, expected tool arguments parse against current typed
contracts, explicit handoff examples hit the deterministic keyword path, and
price-fabrication examples are recognized by the plain-text guard.

No production code loads this fixture.
