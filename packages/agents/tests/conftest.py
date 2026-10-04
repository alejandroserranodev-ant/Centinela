# The tests marked modelo run the agents against the model and the kernel the root .env names.
# They load that file and .env.local over it, and skip when the provider or the database is unusable.
import os
from pathlib import Path

import psycopg
import pytest
import requests

ROOT = Path(__file__).resolve().parents[3]


def load_root_env() -> None:
    for name, override in ((".env", False), (".env.local", True)):
        path = ROOT / name
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        for line in lines:
            key, separator, value = line.partition("=")
            if separator and not line.startswith("#") and (override or not os.environ.get(key.strip())):
                os.environ[key.strip()] = value.strip()


def unreachable() -> str | None:
    load_root_env()
    if os.environ.get("LLM_PROVIDER", "ollama") == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            return "OPENAI_API_KEY is empty; it goes in .env.local"
    else:
        try:
            requests.get(f"{os.environ.get('OLLAMA_API_URL', 'http://localhost:11434')}/api/tags", timeout=2).raise_for_status()
        except requests.RequestException:
            return "Ollama does not answer at OLLAMA_API_URL"
    try:
        psycopg.connect(os.environ.get("CENTINELA_KERNEL_DSN", ""), connect_timeout=2).close()
    except psycopg.Error:
        return "the kernel's database does not answer at CENTINELA_KERNEL_DSN"
    return None


def pytest_collection_modifyitems(config, items):
    marked = [item for item in items if "modelo" in item.keywords]
    reason = unreachable() if marked else None
    for item in marked if reason else []:
        item.add_marker(pytest.mark.skip(reason=reason))
