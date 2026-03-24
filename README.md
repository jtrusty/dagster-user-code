# dagster-user-code

Production-oriented Dagster user-code image for running a gRPC code location on Kubernetes.

## What is included

- Dagster `1.12.20` runtime packages aligned with the current published control-plane release train
- Dagster integration packages aligned on the matching `0.28.20` release line
- A minimal placeholder code location in `src/dagster_user_code`
- A Dockerfile for the Dagster gRPC server image
- GitHub Actions workflow to publish to GHCR on `main`, `master`, tags, and manual dispatch

## Runtime notes

- This image intentionally does not include `dagster-webserver`
- The image currently targets Python `3.13`, which is the newest broadly compatible line across the selected runtime packages
- The default dbt adapter is `dbt-spark`; swap it if your actual target is Databricks or something else
- `pyspark` and `delta-spark` should be pinned after confirming the Spark version you run in-cluster
- The Docker build uses `constraints.txt` to keep `pip` resolution stable for the published image
- The Docker image installs the `aws`, `dbt`, and `spark` extras by default; you can override that with the `INSTALL_EXTRAS` build arg

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[aws,dbt,spark,dev]"
dagster api grpc -h 0.0.0.0 -p 4000 -m dagster_user_code.definitions
```
