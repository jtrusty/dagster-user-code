from dagster import Definitions, asset


@asset
def healthcheck_asset() -> str:
    return "ok"


defs = Definitions(assets=[healthcheck_asset])

