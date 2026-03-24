import importlib

from dagster_user_code.bootstrap import configured_module, ensure_package_installed

ensure_package_installed()

defs = importlib.import_module(configured_module()).defs
