# Google ADK Ecommerce Agent

## Purpose

The agent adds a conversational analysis layer around the existing ETL pipeline.
It does not replace or modify the deterministic pipeline.

```text
User
  -> Google ADK root agent (Gemini)
  -> approved Python function tool
  -> read-only BigQuery request
  -> structured result
  -> natural-language explanation
```

The first version deliberately has no arbitrary SQL tool, write tool, or pipeline
execution tool.

## Project Files

```text
python/src/agents/ecommerce_data_agent/
  __init__.py       ADK package discovery
  agent.py          Gemini model, instructions, and registered tools
  agent_callbacks.py data-scope guard and Gemini latency logging

python/src/agent_tools/
  bigquery_tools.py fixed, read-only BigQuery tools

tests/
  test_bigquery_agent_tools.py
```

The agent has six tools:

| Tool | Data source | Purpose |
| --- | --- | --- |
| `get_sales_summary` | Gold | Revenue, orders, items, and average order value |
| `get_top_products` | Gold | Highest-revenue products |
| `get_top_customers` | Gold | Highest-spending customer IDs |
| `get_recent_daily_sales` | Gold | Latest daily sales rows |
| `get_data_quality_report` | Silver | Counts for every validation failure |
| `get_pipeline_row_counts` | All layers | Row counts and missing-table detection |

## Step 1: Create the Python Environment

Run these commands from the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Confirm that ADK is available:

```powershell
adk --help
python -m pip show google-adk google-genai
```

Use ADK 1.37 or later in the 1.x series together with Google Gen AI SDK 2.x.
The two packages are constrained together in `requirements.txt` because older ADK
versions require an SDK that uses the retired Interactions API schema.

## Step 2: Configure the Environment

The existing root `.env` remains private and is already ignored by Git. Use
`.env.example` only as a list of required names. Do not commit an API key or
service-account file.

Confirm the ETL and dataset settings in `.env`:

```dotenv
GCP_PROJECT_ID=your-gcp-project-id
GCP_CREDENTIALS_FILE=credentials/service-account.json
BQ_DATASET=ecommerce_staging
BQ_SILVER_DATASET=ecommerce_silver
BQ_GOLD_DATASET=ecommerce_gold
ADK_MODEL=gemini-3.5-flash-lite
ADK_BQ_MAXIMUM_BYTES_BILLED=104857600
```

`ADK_BQ_MAXIMUM_BYTES_BILLED` is a per-query safety limit. The default is
104857600 bytes, or 100 MiB.

`gemini-3.5-flash-lite` is used because these are simple, fixed database lookups.
It is Google's low-latency Flash-Lite model and defaults to minimal thinking.

The agent uses ADK's Gemini Interactions API adapter. This endpoint supports the
current Gemini model and the agent's custom BigQuery function tools.

## Step 3: Choose Gemini Authentication

Use exactly one of the following options.

### Option A: Vertex AI

This is the natural choice when the trainer wants the agent fully connected to
Google Cloud.

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account.json
```

The service account needs enough permission to invoke the selected Vertex AI
model, create BigQuery query jobs, and read the approved datasets.

### Option B: Google AI Studio

This is simpler for a local demonstration. Gemini uses the API key, while the
BigQuery tools continue using `GCP_CREDENTIALS_FILE`.

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your-gemini-api-key
```

Remove or comment out the Vertex AI variables when using this mode.

## Step 4: Confirm the ETL Data

Run the existing pipeline before asking the agent about current data:

```powershell
python -m python.src.main
```

The agent reads the resulting staging, Silver, and Gold tables. It does not run
this command itself.

## Step 5: Run the Tool Tests

The tests use fake BigQuery clients and do not consume BigQuery or Gemini quota:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## Step 6: Run the Agent in the Terminal

Run this from the repository root:

```powershell
adk run python/src/agents/ecommerce_data_agent
```

Type `exit` to finish the session.

## Step 7: Run the ADK Development Web Interface

Run this from the repository root:

```powershell
adk web --port 8000 python/src/agents
```

Open `http://localhost:8000` and select `ecommerce_data_agent`. The ADK web
interface is a local development and debugging interface, not a production UI.

## Questions to Test

Use this order for a trainer demonstration:

1. `Are all expected staging, Silver, and Gold tables available?`
2. `What is our total revenue and average order value?`
3. `Show the top five products by revenue.`
4. `Which Silver validation checks are failing?`
5. `Why might revenue be null or lower than expected?`
6. `Show the latest daily sales figures.`
7. `Who is the prime minister of India?`

For the fifth question, the agent is instructed to call the sales summary,
quality report, and row-count tools before giving a diagnosis.

The seventh question is a negative scope test. It must return the fixed message
that the agent can only answer questions about ecommerce pipeline data. Gemini
and BigQuery are not called for that request.

## Safety Design

- Table names and queries are defined in Python, not supplied by the model.
- Every query is read-only and has a maximum-bytes-billed limit.
- User list requests are capped at 20 products or customers and 90 daily rows.
- Customer names and email addresses are not returned by the tools.
- Tool results are converted to JSON-safe values before Gemini receives them.
- Missing tables and permission errors are returned as structured tool errors.
- A deterministic callback blocks unrelated questions before a model call.
- Mixed-topic requests are instructed to receive only the pipeline-data answer.
- Local ADK session data and saved sessions are ignored by Git.

## Performance Behavior

- The authenticated BigQuery client is created once and reused until the agent
  process exits.
- BigQuery query caching remains enabled.
- Gemini calls and BigQuery operations log their elapsed time in seconds.
- Model output is capped at 512 tokens, and Flash-Lite defaults to minimal thinking.
- The first valid question can still be slower while libraries, authentication,
  and network connections initialize.

## Troubleshooting

`adk` is not recognized:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`The legacy Interactions API schema is no longer supported`:

```powershell
python -m pip install --upgrade "google-adk>=1.37,<2" "google-genai>=2.9,<3"
python -m pip show google-adk google-genai
```

Upgrade both packages together. ADK 1.29 constrains `google-genai` below 2.0,
so upgrading only `google-genai` creates an incompatible environment.

Gemini authentication fails:

- Verify that only one authentication mode is configured.
- For Vertex AI, check project, location, service-account path, and model access.
- For AI Studio, check `GOOGLE_API_KEY` and `GOOGLE_GENAI_USE_VERTEXAI=FALSE`.

BigQuery returns a configuration error:

- Check `GCP_PROJECT_ID` and the three dataset names.
- Check that `GCP_CREDENTIALS_FILE` points to an existing private JSON file.
- Check that the service account can create query jobs and read the datasets.

A query exceeds the byte limit:

- Keep the safety limit in place for normal use.
- Review the query and expected scan size before increasing
  `ADK_BQ_MAXIMUM_BYTES_BILLED`.

The agent still responds slowly:

- Compare the `Gemini model call completed` and `BigQuery request completed`
  timing lines in the terminal log.
- Ask a focused question such as `Show the top five products by revenue.`
- Restart the agent after changing `.env`; model and client configuration are
  loaded when the process starts.
- The pipeline row-count question checks 13 table metadata records and can take
  longer than one Gold KPI query.

## Next Development Phases

After the single agent is tested and evaluated, suitable additions are anomaly
detection, pipeline-log monitoring, formal ADK evaluation cases, and a separate
approval-gated remediation agent. Write capabilities should not be added to the
analyst agent.

Official references:

- [ADK Python quickstart](https://adk.dev/get-started/python/)
- [ADK agent concepts](https://adk.dev/agents/)
- [ADK function tools](https://adk.dev/tools-custom/function-tools/)
- [ADK evaluation](https://adk.dev/evaluate/)
- [ADK safety and security](https://adk.dev/safety/)
