__all__ = ["defs"]


def __getattr__(name: str):
    if name == "defs":
        from dagster_user_code.definitions import defs

        return defs
    raise AttributeError(name)
