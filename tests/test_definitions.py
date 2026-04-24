import importlib
import sys
import types


def test_definitions_load() -> None:
    fake_package = types.ModuleType("fake_package")
    fake_package.__path__ = []
    fake_defs_module = types.ModuleType("fake_package.fake_defs")
    fake_defs_module.defs = object()

    sys.modules["fake_package"] = fake_package
    sys.modules["fake_package.fake_defs"] = fake_defs_module
    sys.modules.pop("dagster_user_code.definitions", None)

    import dagster_user_code.bootstrap as bootstrap

    original_ensure = bootstrap.ensure_package_installed
    original_module = bootstrap.configured_module
    bootstrap.ensure_package_installed = lambda: None
    bootstrap.configured_module = lambda: "fake_package.fake_defs"
    try:
        definitions = importlib.import_module("dagster_user_code.definitions")
        assert definitions.defs is fake_defs_module.defs
    finally:
        bootstrap.ensure_package_installed = original_ensure
        bootstrap.configured_module = original_module
        sys.modules.pop("dagster_user_code.definitions", None)
        sys.modules.pop("fake_package.fake_defs", None)
        sys.modules.pop("fake_package", None)
