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

The project includes a scoped Google ADK multi-agent system for date-aware Gold
analytics, Silver data-quality diagnosis, post-pipeline monitoring, anomaly
detection, BigQuery ML forecasting, and human-approved correction proposals.
Analytics remain read-only; approved proposals only produce manual,
parameterized SQL and never execute database changes.

See [Google ADK Agent Guide](docs/google-adk-agent.md) for setup,
authentication, triggers, testing, evaluations, example prompts, and local run
commands.
