# Google ADK Ecommerce Agent

## What We Built

The Google ADK layer sits around the deterministic ETL pipeline. It reads the
data produced by the pipeline, answers ecommerce questions, monitors quality,
finds unusual sales activity, and prepares corrections for human review.

```text
MySQL -> GCS -> BigQuery staging -> Silver -> Gold
                                           |
                                           v
                              Google ADK root agent
                              |       |       |
                              v       v       v
                           quality  monitor  forecast
                                                |
                                                v
                                      remediation proposals
                                      (human approval only)
```

The SQL pipeline remains the source of truth. The language model chooses among
small, fixed Python tools; it does not receive an unrestricted SQL console or
database credentials.

## Agent Architecture

`ecommerce_data_agent` is the root business agent. Simple KPI questions stay on
this fast path. More specialized requests are delegated to four sub-agents:

| Agent | Responsibility |
| --- | --- |
| Root business agent | Sales KPIs, date filters, comparisons, products, customers, and categories |
| Data-quality agent | Silver validation failures and layer row counts |
| Pipeline-monitor agent | Latest pipeline health and post-run monitoring |
| Anomaly/forecast agent | Rolling anomalies and BigQuery ML forecasts |
| Remediation agent | Create, approve, reject, and render correction proposals |

Important files:

```text
python/src/agents/ecommerce_data_agent/
  agent.py                         root agent and business tools
  sub_agents.py                    four specialist agents
  agent_callbacks.py               scope guard and latency logging
  advanced_behaviors.evalset.json  ADK behavior evaluations

python/src/agent_tools/
  bigquery_tools.py                core KPI and quality tools
  advanced_analytics_tools.py      comparisons and date-filtered rankings
  monitoring_tools.py              combined pipeline health report
  ml_tools.py                      anomaly and BigQuery ML tools
  remediation_tools.py             approval-only correction proposals

python/src/pipeline_monitor.py      post-run report and sanitized failure history
sql/ml/                             BigQuery ML dataset, model, and query SQL
runtime/                            ignored local reports and proposals
```

## Capabilities

The agent can:

- Return all-time or inclusive date-range orders, items, revenue, and average
  order value.
- Compare two periods with absolute values and percentage changes.
- Rank products or customers for a selected date range.
- Group revenue by category for a selected date range.
- Count failed Silver validation checks and missing tables.
- Build a combined pipeline health result with healthy, warning, or critical
  status.
- Detect recent revenue or order anomalies with a rolling statistical baseline.
- Read a BigQuery ML revenue forecast and model-based anomalies when a model is
  available.
- Create a tightly allowlisted data-correction proposal, require explicit human
  approval, and produce parameterized MySQL for manual execution.

It deliberately cannot answer general-knowledge questions. A deterministic
callback blocks requests such as `Who is the prime minister of India?` before
Gemini or BigQuery is called.

## Install

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Confirm the compatible ADK packages:

```powershell
adk --help
python -m pip show google-adk google-genai
```

The project requires Google ADK 1.37 or later in the 1.x series and Google Gen
AI SDK 2.x. Keep both packages within the ranges in `requirements.txt`.

## Configure

Keep real values in the ignored `.env`; use `.env.example` as the template.
Never commit API keys or service-account files.

```dotenv
GCP_PROJECT_ID=your-gcp-project-id
GCP_CREDENTIALS_FILE=credentials/service-account.json
BQ_DATASET=ecommerce_staging
BQ_SILVER_DATASET=ecommerce_silver
BQ_GOLD_DATASET=ecommerce_gold
BQ_ML_DATASET=ecommerce_ml

ADK_MODEL=gemini-3.5-flash-lite
ADK_BQ_MAXIMUM_BYTES_BILLED=104857600

POST_PIPELINE_MONITOR_ENABLED=TRUE
PIPELINE_INVALID_ROW_THRESHOLD=0
BQML_TRAINING_ENABLED=FALSE
```

`POST_PIPELINE_MONITOR_ENABLED=TRUE` triggers a health check after Gold tables
finish. Its latest result is written to `runtime/latest_pipeline_health.json`.
Pipeline exceptions are sanitized and appended to
`runtime/pipeline_failures.jsonl`; the monitor agent can read recent events.

`BQML_TRAINING_ENABLED=FALSE` is intentional. Model creation can consume
BigQuery quota and needs additional permissions. Set it to `TRUE` only when you
want the ETL run to create or replace the forecast model.

Choose one Gemini authentication method.

Vertex AI:

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account.json
```

Google AI Studio:

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your-gemini-api-key
```

## Run The Pipeline

```powershell
python -m python.src.main
```

The run performs extraction, staging, Silver, Gold, and the health trigger. If
BigQuery ML training is enabled, it also creates the ML dataset and daily
revenue forecast model before monitoring.

For an existing warehouse, the same BigQuery ML objects can be created manually
from these templates:

```text
sql/ml/create_ml_dataset.sql
sql/ml/create_daily_revenue_forecast_model.sql
```

Replace the project and dataset placeholders before submitting them. Forecast
tools return a structured `model unavailable` error until the model exists.

## Run The Agent

Terminal:

```powershell
adk run python/src/agents/ecommerce_data_agent
```

ADK development web interface:

```powershell
adk web --port 8000 python/src/agents
```

Then open `http://localhost:8000` and select `ecommerce_data_agent`. Restart the
agent after changing `.env`, because configuration is loaded at startup.

## Questions To Test

1. `What are our total revenue, orders, items sold, and average order value?`
2. `How many orders and items were sold from 2025-01-01 through 2025-02-28?`
3. `Compare sales from January 2025 with February 2025.`
4. `Show the top five products by revenue from 2025-01-01 to 2025-02-28.`
5. `Show the top five customers by spending in February 2025.`
6. `Show revenue by category for February 2025.`
7. `Which Silver validation checks are failing?`
8. `Run a complete pipeline health check.`
9. `Were there unusual sales days in the last 90 days?`
10. `Forecast revenue for the next 14 days.`
11. `Who is the prime minister of India?`

Question 11 is the negative scope test. It must return only the fixed
ecommerce-data boundary message.

The warehouse does not define a currency, so the agent reports monetary values
without inventing `$`, `INR`, or another currency symbol.

## Approved Correction Flow

Corrections are intentionally separated from analytics:

1. Ask the remediation agent to propose a correction to an allowlisted field.
2. Review the proposal ID, table, record, field, proposed value, and reason.
3. Explicitly approve or reject that proposal by ID.
4. After approval, request its parameterized MySQL script.
5. A human reviews and executes the script outside the agent.

Approval never executes SQL. The agent has no database-update tool. Proposals
are stored locally in the ignored `runtime/remediation_proposals.json` file.

## Tests And Evaluations

Unit and integration tests use fake clients, so they do not consume Gemini or
BigQuery quota:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Run the seven ADK behavior scenarios when Gemini and BigQuery are available:

```powershell
adk eval python/src/agents/ecommerce_data_agent/__init__.py python/src/agents/ecommerce_data_agent/advanced_behaviors.evalset.json --print_detailed_results
```

The eval set covers date selection, comparisons, rankings, specialist routing,
forecast wording, human approval, and the general-knowledge scope block.

## Safety And Cost Controls

- All analytics queries are fixed, read-only SQL with typed parameters.
- User-controlled sort fields and editable columns use strict allowlists.
- BigQuery queries have a configurable maximum-bytes-billed limit.
- Product and customer lists are capped at 20 rows.
- Customer email addresses are not returned to Gemini.
- Tool output is converted to JSON-safe values.
- Missing resources and permission failures become structured tool errors.
- The root callback blocks unrelated requests before a model call.
- The remediation agent can only prepare manual, parameterized scripts.
- BigQuery ML training is disabled by default.
- Local ADK sessions, runtime reports, credentials, and `.env` are ignored.

## Performance

- One authenticated BigQuery client is reused for the process lifetime.
- BigQuery query caching stays enabled.
- Gemini and BigQuery elapsed times are logged.
- Flash-Lite uses minimal thinking and a 512-token response cap.
- Focused Gold queries are faster than full row-count or quality checks.
- The first request may be slower while authentication and connections warm up.

## Trainer Questions

- Why use deterministic tools instead of letting the model generate arbitrary SQL?
- How should we measure tool-selection accuracy and answer correctness separately?
- What anomaly threshold and lookback period fit our business seasonality?
- How often should the ARIMA model be retrained, and how should forecast drift be measured?
- Should monitoring run in Cloud Scheduler, Composer, or after the existing ETL job?
- Which IAM roles give query access without granting unnecessary write permissions?
- What evidence should a human see before approving a source-data correction?
- When should each specialist become a separate deployed service instead of an ADK sub-agent?

## Troubleshooting

If `adk` is not recognized, activate `.venv` and install `requirements.txt`.

If Gemini authentication fails, verify that exactly one authentication method
is configured and that the selected model is available in its project/location.

If BigQuery fails, verify all dataset names, the private credential path, query
job permission, table read permission, and the byte limit.

If forecasts say the model is unavailable, enable BigQuery ML training or create
the SQL objects manually, then confirm the service account has BigQuery ML
permissions.

If answers are slow, compare the logged Gemini and BigQuery timings. Restart the
agent after configuration changes and test with one focused Gold KPI question.

Official references:

- [ADK Python quickstart](https://adk.dev/get-started/python/)
- [ADK agent concepts](https://adk.dev/agents/)
- [ADK workflow agents](https://adk.dev/agents/workflow-agents/)
- [ADK function tools](https://adk.dev/tools-custom/function-tools/)
- [ADK evaluation](https://adk.dev/evaluate/)
- [ADK safety and security](https://adk.dev/safety/)
- [BigQuery ML time-series models](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-time-series)
- [BigQuery ML anomaly detection](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-detect-anomalies)
