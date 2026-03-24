# dagster-user-code

Production-oriented Dagster user-code image for running a gRPC code location on Kubernetes.

## What is included

- Dagster `1.12.14` runtime packages aligned with the control plane
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

## Image publishing

The GitHub Actions workflow publishes to:

```text
ghcr.io/<owner>/<repo>
```

Package write permissions are handled with the repository `GITHUB_TOKEN`.

## Dependency updates

Renovate is configured in `renovate.json` to:

- group Dagster package updates together
- group dbt updates together
- group Spark runtime updates together
- require approval from the dependency dashboard before major upgrades for core data runtime packages

Install the Renovate GitHub App for this repository to activate it.
