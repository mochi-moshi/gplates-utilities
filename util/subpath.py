import os


def is_subpath(path: str, base: str) -> bool:
    real_path = os.path.realpath(path)
    real_base = os.path.realpath(base)

    return real_path.startswith(real_base)
