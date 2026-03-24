from dagster_user_code import defs


def test_definitions_load() -> None:
    assert defs is not None
