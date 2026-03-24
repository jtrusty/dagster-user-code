# dagster-user-code

Production-oriented Dagster user-code image for running a gRPC code location on Kubernetes.

## What is included

- Dagster `1.12.14` runtime packages aligned with the control plane
- Dagster integration packages aligned on the matching `0.28.14` release line
- A minimal placeholder code location in `src/dagster_user_code`
- A Dockerfile for the Dagster gRPC server image
- GitHub Actions workflow to publish to GHCR on `main`, `master`, tags, and manual dispatch

## Runtime notes

- This image intentionally does not include `dagster-webserver`
- The default dbt adapter is `dbt-spark`; swap it if your actual target is Databricks or something else
- `pyspark` and `delta-spark` should be pinned after confirming the Spark version you run in-cluster

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
dagster api grpc -h 0.0.0.0 -p 4000 -m dagster_user_code.definitions
```
