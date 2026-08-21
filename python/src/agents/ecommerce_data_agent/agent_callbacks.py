"""Scope enforcement and latency callbacks for the ecommerce data agent."""

from __future__ import annotations

import logging
import re
from time import perf_counter

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types


LOGGER = logging.getLogger(__name__)

OUT_OF_SCOPE_MESSAGE = (
    "I can only answer questions about your ecommerce pipeline data in BigQuery: "
    "sales, products, customers, daily KPIs, Silver data quality, and pipeline "
    "table counts."
)

_SCOPE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:e-?commerce|mysql|gcs|bigquery|etl|pipeline)\b",
        r"\b(?:staging|bronze|silver|gold)\b",
        r"\b(?:sale|sales|revenue|order|orders|product|products|customer|customers)\b",
        r"\b(?:average order value|aov|units sold|items sold|items purchased)\b",
        r"\b(?:top selling|best selling|total spending|daily sales)\b",
        r"\b(?:data quality|validation|invalid rows?|row counts?|missing tables?)\b",
        r"\b(?:compare|comparison|trend|forecast|anomaly|anomalies)\b",
        r"\b(?:pipeline health|monitor|monitoring|remediation|proposal)\b",
        r"\b(?:approve|approval|reject|correction|source data fix)\b",
    )
)

_SCOPE_HELP_REQUESTS = {
    "what can you do",
    "what questions can i ask",
    "show your capabilities",
    "show available questions",
}

_MODEL_CALL_STARTS: dict[str, float] = {}


def is_ecommerce_data_question(message: str) -> bool:
    """Return whether a message belongs to the agent's approved data scope."""
    normalized = " ".join(message.lower().strip().split()).rstrip("?.!")
    if normalized in _SCOPE_HELP_REQUESTS:
        return True
    return any(pattern.search(message) for pattern in _SCOPE_PATTERNS)


def _latest_user_message(llm_request: LlmRequest) -> str:
    for content in reversed(llm_request.contents):
        if content.role != "user" or not content.parts:
            continue
        text = " ".join(part.text for part in content.parts if part.text).strip()
        if text:
            return text
    return ""


def enforce_data_scope(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """Block unrelated requests before they consume a Gemini model call."""
    message = _latest_user_message(llm_request)
    if not is_ecommerce_data_question(message):
        LOGGER.info(
            "Blocked an out-of-scope request before the model call (invocation=%s).",
            callback_context.invocation_id,
        )
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=OUT_OF_SCOPE_MESSAGE)],
            )
        )

    _MODEL_CALL_STARTS[callback_context.invocation_id] = perf_counter()
    return None


def log_model_latency(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """Log elapsed Gemini time without modifying its response."""
    started_at = _MODEL_CALL_STARTS.pop(callback_context.invocation_id, None)
    if started_at is not None:
        LOGGER.info(
            "Gemini model call completed in %.2f seconds (invocation=%s).",
            perf_counter() - started_at,
            callback_context.invocation_id,
        )
    return None
