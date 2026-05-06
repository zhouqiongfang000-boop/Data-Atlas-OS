import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
TRUE_VALUES = {"1", "true", "yes", "on"}


def load_env_file(env_file: Path = ENV_FILE) -> None:
    if not env_file.exists():
        return

    try:
        content = env_file.read_text(encoding="utf-8")
    except OSError:
        return

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        cleaned_value = value.strip().strip('"').strip("'")
        os.environ[key] = cleaned_value


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default

    stripped_value = value.strip()
    return stripped_value if stripped_value else default


def get_bool_env(name: str, default: bool = False) -> bool:
    value = get_env(name)
    if value is None:
        return default
    return value.lower() in TRUE_VALUES


def get_int_env(name: str, default: int) -> int:
    value = get_env(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_list_env(name: str, default: list[str] | None = None) -> list[str]:
    value = get_env(name)
    if value is None:
        return list(default or [])

    items = [item.strip().rstrip("/") for item in value.split(",") if item.strip()]
    return items or list(default or [])


def get_app_env() -> str:
    return (get_env("APP_ENV", "development") or "development").lower()


def is_production_env() -> bool:
    return get_app_env() == "production"


def require_env(name: str) -> str:
    value = get_env(name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
