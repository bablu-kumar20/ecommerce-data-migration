# Ecommerce Data Migration

An ecommerce ETL pipeline that extracts MySQL tables, stores CSV files in Google
Cloud Storage, and builds staging, Silver, and Gold datasets in BigQuery.

```text
MySQL -> GCS -> BigQuery staging -> Silver -> Gold
```

Run the ETL pipeline from the repository root:

```powershell
python -m python.src.main
```

## Google ADK Agent

The project includes a read-only Google ADK agent for Gold KPI questions,
Silver data-quality diagnosis, and pipeline row-count checks.

See [Google ADK Agent Guide](docs/google-adk-agent.md) for setup,
authentication, testing, example prompts, and local run commands.
