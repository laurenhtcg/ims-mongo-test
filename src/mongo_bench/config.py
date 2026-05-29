"""Application settings loaded from the environment (scaffold — no validation yet).

``load_settings()`` runs ``python-dotenv`` first (see ``_load_dotenv``). Call ``load_settings()``
before reading other ``os.environ`` keys (e.g. ``BENCH_*``) so ``.env`` is applied. Variables
already set in the environment (including by Docker Compose) are not overwritten.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_dotenv_loaded = False


def _load_dotenv() -> None:
    """Load ``.env`` into ``os.environ`` (does not override variables already set in the shell).

    Tries, in order:

    1. Path from ``MONGO_BENCH_DOTENV`` if set.
    2. ``.env`` in the current working directory.
    3. ``.env`` next to the project root when running from an editable install (``…/src/mongo_bench/config.py``).
    """
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    if path := os.environ.get("MONGO_BENCH_DOTENV"):
        load_dotenv(path, override=False)
        return

    cwd_env = Path.cwd() / ".env"
    if cwd_env.is_file():
        load_dotenv(cwd_env, override=False)

    here = Path(__file__).resolve()
    if here.parent.name == "mongo_bench" and here.name == "config.py":
        repo_env = here.parents[2] / ".env"
        if repo_env.is_file():
            try:
                if repo_env.resolve() != cwd_env.resolve():
                    load_dotenv(repo_env, override=False)
            except OSError:
                load_dotenv(repo_env, override=False)


@dataclass(frozen=True)
class Settings:
    """Holds connection-related settings for future MongoDB use."""

    mongodb_uri: str
    mongodb_db: str


def load_settings() -> Settings:
    """Read settings from environment variables (after loading optional ``.env`` files)."""
    _load_dotenv()
    return Settings(
        mongodb_uri=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
        mongodb_db=os.environ.get("MONGODB_DB", "mongo_bench"),
    )
