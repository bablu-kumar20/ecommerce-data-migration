"""Specialized ADK agents for quality, monitoring, ML, and remediation."""

from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import types

from python.src.agent_tools.bigquery_tools import (
    get_data_quality_report,
    get_pipeline_row_counts,
)
from python.src.agent_tools.ml_tools import (
    detect_recent_sales_anomalies,
    get_ml_revenue_anomalies,
    get_revenue_forecast,
)
from python.src.agent_tools.monitoring_tools import get_pipeline_health_report
from python.src.agent_tools.remediation_tools import (
    approve_remediation_proposal,
    create_remediation_proposal,
    get_approved_remediation_script,
    get_remediation_proposal,
    reject_remediation_proposal,
)
from .agent_callbacks import (
    enforce_data_scope,
    log_model_latency,
)
from python.src.pipeline_monitor import (
    get_latest_local_pipeline_report,
    get_recent_pipeline_failures,
)


def _model() -> Gemini:
    return Gemini(
        model=os.getenv("ADK_MODEL", "gemini-3.5-flash-lite"),
        use_interactions_api=True,
    )


def _generation_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(max_output_tokens=512)


data_quality_agent = Agent(
    name="data_quality_agent",
    model=_model(),
    description=(
        "Investigates Silver validation failures, missing tables, empty tables, "
        "and row-count health for the ecommerce pipeline."
    ),
    instruction="""
You are the ecommerce Silver data-quality specialist.
- Use a tool for every claim about current data.
- Explain failed checks by table and validation flag.
- Do not invent source rows or claim that you repaired data.
- Keep the response concise and name the Silver or metadata source.
""".strip(),
    tools=[get_data_quality_report, get_pipeline_row_counts],
    generate_content_config=_generation_config(),
    before_model_callback=enforce_data_scope,
    after_model_callback=log_model_latency,
)


pipeline_monitor_agent = Agent(
    name="pipeline_monitor_agent",
    model=_model(),
    description=(
        "Explains overall pipeline health, post-run reports, missing tables, "
        "quality warnings, and ETL monitoring issues."
    ),
    instruction="""
You are the ecommerce pipeline monitoring specialist.
- Use get_pipeline_health_report for live health questions.
- Use get_latest_local_pipeline_report only when asked about the last ETL run.
- Use get_recent_pipeline_failures for the latest failed ETL stages and errors.
- Distinguish healthy, warning, critical, error, and unavailable states.
- Never claim that monitoring repaired or reran the pipeline.
""".strip(),
    tools=[
        get_pipeline_health_report,
        get_latest_local_pipeline_report,
        get_recent_pipeline_failures,
    ],
    generate_content_config=_generation_config(),
    before_model_callback=enforce_data_scope,
    after_model_callback=log_model_latency,
)


anomaly_forecast_agent = Agent(
    name="anomaly_forecast_agent",
    model=_model(),
    description=(
        "Detects unusual ecommerce sales behavior and reads optional BigQuery ML "
        "revenue forecasts and model-based anomalies."
    ),
    instruction="""
You are the ecommerce anomaly and forecasting specialist.
- Use the rolling anomaly tool unless the user explicitly asks for BigQuery ML.
- Forecasts are estimates, not actual revenue. Always state horizon and confidence.
- If the ML model is missing, explain that BQML_TRAINING_ENABLED must be enabled
  for a pipeline run or the model SQL must be run manually.
- Do not attach a currency symbol because the source currency is unspecified.
""".strip(),
    tools=[
        detect_recent_sales_anomalies,
        get_revenue_forecast,
        get_ml_revenue_anomalies,
    ],
    generate_content_config=_generation_config(),
    before_model_callback=enforce_data_scope,
    after_model_callback=log_model_latency,
)


remediation_agent = Agent(
    name="remediation_agent",
    model=_model(),
    description=(
        "Creates, reviews, approves, or rejects allowlisted source-data correction "
        "proposals without executing database writes."
    ),
    instruction="""
You are the approval-gated ecommerce remediation specialist.
- Creating a proposal never changes data.
- Call approve_remediation_proposal only when the user explicitly provides the
  proposal ID, approver identity, and confirms approval.
- Never infer approval from a vague response.
- An approved script is parameterized and manual-only. Never claim it was executed.
- Never request passwords, service-account contents, or unrestricted SQL access.
""".strip(),
    tools=[
        create_remediation_proposal,
        approve_remediation_proposal,
        reject_remediation_proposal,
        get_remediation_proposal,
        get_approved_remediation_script,
    ],
    generate_content_config=_generation_config(),
    before_model_callback=enforce_data_scope,
    after_model_callback=log_model_latency,
)
