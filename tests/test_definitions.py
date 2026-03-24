import importlib
import sys
import types


def test_definitions_load() -> None:
    fake_package = types.ModuleType("stock_screener")
    fake_package.__path__ = []
    fake_defs_module = types.ModuleType("stock_screener.dagster_defs")
    fake_defs_module.defs = object()

    sys.modules["stock_screener"] = fake_package
    sys.modules["stock_screener.dagster_defs"] = fake_defs_module
    sys.modules.pop("dagster_user_code.definitions", None)

    import dagster_user_code.bootstrap as bootstrap

    original = bootstrap.ensure_stock_screener_installed
    bootstrap.ensure_stock_screener_installed = lambda: None
    try:
        definitions = importlib.import_module("dagster_user_code.definitions")
        assert definitions.defs is fake_defs_module.defs
    finally:
        bootstrap.ensure_stock_screener_installed = original
        sys.modules.pop("dagster_user_code.definitions", None)
        sys.modules.pop("stock_screener.dagster_defs", None)
        sys.modules.pop("stock_screener", None)
