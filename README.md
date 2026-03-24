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
- The image currently targets Python `3.13` because `dagster-dbt` `0.28.20` currently declares `Requires-Python <3.14`
- The default dbt adapter is `dbt-spark`; swap it if your actual target is Databricks or something else
- `pyspark` and `delta-spark` should be pinned after confirming the Spark version you run in-cluster
- The Docker build installs from `uv.lock`, so dependency resolution happens before image build time
- The Docker image installs the `aws`, `dbt`, and `spark` extras by default; you can override that with the `INSTALL_EXTRAS` build arg

## Local development

```bash
uv sync --extra aws --extra dbt --extra spark --extra dev
dagster api grpc -h 0.0.0.0 -p 4000 -m dagster_user_code.definitions
```

## Dependency management

This repo uses `uv` for locking and syncing dependencies.

```bash
uv lock
uv lock --upgrade
uv sync --extra aws --extra dbt --extra spark --extra dev
```

Commit `uv.lock` with dependency changes so CI and Docker builds install from a fixed graph.
