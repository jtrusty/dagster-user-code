# dagster-user-code

Production-oriented Dagster user-code image for running a gRPC code location on Kubernetes.

## What is included

- Dagster `1.12.20` runtime packages aligned with the current published control-plane release train
- Dagster integration packages aligned on the matching `0.28.20` release line
- A minimal placeholder code location in `src/dagster_user_code`
- A Dockerfile for the Dagster gRPC server image
- GitHub Actions workflows for GHCR publishing and automated semantic versioning

## Runtime notes

- This image intentionally does not include `dagster-webserver`
- The image currently targets Python `3.13` because `dagster-dbt` `0.28.20` currently declares `Requires-Python <3.14`
- The default dbt adapter is `dbt-spark`; swap it if your actual target is Databricks or something else
- `pyspark` and `delta-spark` should be pinned after confirming the Spark version you run in-cluster
- The Docker build installs from `uv.lock`, so dependency resolution happens before image build time
- The Docker image installs the `aws`, `dbt`, and `spark` extras by default; you can override that with the `INSTALL_EXTRAS` build arg

## Bootstrap model

This image is now a stable Dagster runtime that bootstraps business logic from the active `stock-screener` wheel release.

- On startup, it reads `STOCK_SCREENER_CURRENT_URI` (default: `s3://lakehouse/artifacts/stock-screener/current.txt`)
- It resolves the active wheel from `current.txt`
- It downloads and installs that wheel into a local target directory
- It logs the pointer URI, resolved wheel URI, wheel filename, and inferred package version
- It then serves Dagster definitions from `stock_screener.dagster_defs`

Changing `current.txt` does not hot-reload an already running code server. Promote the new wheel first, then restart the Dagster user-code deployment so the next process startup resolves the new artifact.

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

## Releases

This repo uses `release-please` to manage semantic version tags and changelog updates.

- `fix:` commits produce a patch release
- `feat:` commits produce a minor release
- `feat!:` or `BREAKING CHANGE:` produces a major release
- a release PR is opened automatically from commits on the default branch
- merging that PR creates a GitHub release and a `vX.Y.Z` tag
- the publish workflow then pushes both `latest` and the matching `vX.Y.Z` image tag to GHCR

The package version in `pyproject.toml`, the git tag, and the changelog are all updated by `release-please`.
