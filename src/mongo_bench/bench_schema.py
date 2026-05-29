"""Ensure benchmark collections and indexes exist.

The canonical specification lives in ``mongo_bench/resources/bench_collections.json``.
Reference that path (or this module) in test plans so runs are reproducible.

Each collection in the spec is created when missing (needed when a collection has Atlas Search
indexes but no MongoDB ``create_index`` entries, e.g. ``bench_search``). Duplicate
``createCollection`` calls are avoided by checking ``list_collection_names`` first.

Run as a small CLI (same behavior as ``mongo-bench init``)::

    python -m mongo_bench.bench_schema [--skip-search-indexes]

In Docker, the image entrypoint is ``mongo-bench``, so override entrypoint to use Python::

    docker compose run --rm --entrypoint python job-populate-default -m mongo_bench.bench_schema

Atlas Search index creation requires MongoDB 7.0+ **Atlas** (not supported on a plain
``mongo`` Docker image). When Search is unavailable, set ``MONGO_BENCH_SKIP_SEARCH_INDEXES=1``
to skip those steps, or rely on the default try-and-warn behavior.
"""

from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from importlib import resources
from typing import Any, Mapping

from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

_RESOURCE = "bench_collections.json"


@lru_cache(maxsize=1)
def load_bench_collection_specs() -> Mapping[str, Any]:
    """Load and parse ``bench_collections.json`` (cached)."""
    text = resources.files("mongo_bench.resources").joinpath(_RESOURCE).read_text(encoding="utf-8")
    return json.loads(text)


def bench_collection_names() -> tuple[str, ...]:
    """Collection names defined in the benchmark schema (single source of truth)."""
    specs = load_bench_collection_specs()
    return tuple(c["name"] for c in specs["collections"])


def _normalize_index_keys(keys: Any) -> list[tuple[str, int]]:
    """Accept list of [field, direction] pairs or a single-field mapping."""
    if isinstance(keys, dict):
        return [(k, int(v)) for k, v in keys.items()]
    if isinstance(keys, list):
        out: list[tuple[str, int]] = []
        for pair in keys:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError(f"Invalid index keys entry: {pair!r}")
            out.append((str(pair[0]), int(pair[1])))
        return out
    raise TypeError(f"index keys must be list or dict, got {type(keys)}")


def _skip_search_indexes() -> bool:
    return os.environ.get("MONGO_BENCH_SKIP_SEARCH_INDEXES", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _warn(msg: str) -> None:
    print(f"mongo-bench: {msg}", file=sys.stderr)


def _ensure_collection_exists(db: Any, coll_name: str) -> None:
    """Ensure ``coll_name`` exists as a normal collection (empty if newly created).

    ``create_index`` would implicitly create a collection, but ``bench_search`` has no MongoDB
    indexes in the spec, so we must create the namespace before Atlas Search index creation.

    Calling :meth:`~pymongo.database.Database.create_collection` when the collection already exists
    fails (namespace exists); we only call it when ``coll_name`` is not in ``list_collection_names``.
    """
    if coll_name in db.list_collection_names():
        return
    db.create_collection(coll_name)


def _create_collection_index(coll: Any, keys: list[tuple[str, int]], opts: dict[str, Any]) -> None:
    """Create a MongoDB index if it is not already present (by ``name`` when given).

    If an index with the same name already exists, or ``create_index`` reports a
    duplicate/conflict, this is a no-op. Drop indexes manually when you need to
    recreate from ``bench_collections.json``.
    """
    name = opts.get("name")
    if name and name in coll.index_information():
        return
    try:
        coll.create_index(keys, **opts)
    except OperationFailure as exc:
        code = getattr(exc, "code", None)
        detail = getattr(exc, "details", None) or str(exc)
        msg = str(detail).lower()
        # 85 IndexOptionsConflict; 86 IndexKeySpecsConflict; common "already exists" text.
        if code in (85, 86) or "already exists" in msg or "same name" in msg:
            _warn(
                f"Skipping index on {coll.name!r} (name={name!r}): {detail}. "
                "Drop the index manually if it must match a new bench_collections.json spec."
            )
            return
        raise


def _atlas_search_index_names(coll: Any) -> set[str]:
    """Return search index names on ``coll``, or empty set if the server cannot list them."""
    names: set[str] = set()
    try:
        with coll.list_search_indexes() as cursor:
            for doc in cursor:
                n = doc.get("name")
                if isinstance(n, str):
                    names.add(n)
    except (OperationFailure, PyMongoError):
        pass
    return names


def _ensure_atlas_search_index(coll: Any, coll_name: str, name: str, definition: Mapping[str, Any]) -> None:
    """Create an Atlas Search index if it does not already exist on the collection."""
    if name in _atlas_search_index_names(coll):
        return

    try:
        coll.create_search_index({"name": name, "definition": dict(definition)})
    except OperationFailure as exc:
        code = getattr(exc, "code", None)
        detail = getattr(exc, "details", None) or str(exc)
        msg = str(detail).lower()
        if code == 59 or ("no such command" in msg and "createsearchindexes" in msg.replace(" ", "")):
            _warn(
                f"Atlas Search index {name!r} on {coll_name!r} was not created: "
                "this host does not support the createSearchIndexes command (typical for non-Atlas or self-managed MongoDB). "
                "Point MONGODB_URI at an Atlas cluster with Atlas Search, or set MONGO_BENCH_SKIP_SEARCH_INDEXES=1."
            )
            return
        if "already exists" in msg or "duplicate" in msg or code in (85, 86):
            return
        _warn(
            f"Atlas Search index {name!r} on {coll_name!r} was not created "
            f"(code={code!r}): {detail}. "
            "Requires MongoDB 7.0+ on Atlas with Search enabled. "
            "If the definition failed Atlas validation, fix bench_collections.json or adjust the index in Atlas UI."
        )
    except PyMongoError as exc:
        _warn(
            f"Atlas Search index {name!r} on {coll_name!r} was not created: {exc}. "
            "Use MONGO_BENCH_SKIP_SEARCH_INDEXES=1 for deployments without Atlas Search."
        )


def ensure_benchmark_collections(
    client: MongoClient,
    database: str,
    *,
    skip_search_indexes: bool | None = None,
) -> None:
    """Create collections when missing, MongoDB indexes, and Atlas Search indexes.

    :param skip_search_indexes: ``True`` / ``False`` forces behavior; ``None`` reads
        ``MONGO_BENCH_SKIP_SEARCH_INDEXES`` (``1`` / ``true`` / ``yes`` = skip).
    """
    from mongo_bench.config import load_settings

    load_settings()
    if skip_search_indexes is None:
        skip_search_indexes = _skip_search_indexes()

    specs = load_bench_collection_specs()
    db = client[database]

    if skip_search_indexes:
        n_search = sum(len(c.get("atlas_search_indexes", [])) for c in specs["collections"])
        if n_search:
            _warn(
                f"Skipping {n_search} Atlas Search index(es) "
                "(MONGO_BENCH_SKIP_SEARCH_INDEXES is set or --skip-search-indexes was passed)."
            )

    for coll_spec in specs["collections"]:
        coll_name = coll_spec["name"]
        _ensure_collection_exists(db, coll_name)
        coll = db[coll_name]

        for idx in coll_spec.get("indexes", []):
            keys = _normalize_index_keys(idx["keys"])
            opts = dict(idx.get("options", {}))
            _create_collection_index(coll, keys, opts)

        if skip_search_indexes:
            continue

        for sidx in coll_spec.get("atlas_search_indexes", []):
            name = sidx["name"]
            definition = sidx["definition"]
            _ensure_atlas_search_index(coll, coll_name, name, definition)


def ensure_benchmark_collections_from_env(client: MongoClient) -> None:
    """Call :func:`ensure_benchmark_collections` using ``MONGODB_DB`` from settings."""
    from mongo_bench.config import load_settings

    settings = load_settings()
    ensure_benchmark_collections(client, settings.mongodb_db)


def run_cli(argv: list[str] | None = None) -> int:
    """Apply benchmark indexes when run as ``python -m mongo_bench.bench_schema`` (same work as ``mongo-bench init``)."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m mongo_bench.bench_schema",
        description="Ensure benchmark collections, MongoDB indexes, and Atlas Search indexes from bench_collections.json.",
    )
    parser.add_argument(
        "--skip-search-indexes",
        action="store_true",
        help="Skip Atlas Search index creation (otherwise honor MONGO_BENCH_SKIP_SEARCH_INDEXES).",
    )
    args = parser.parse_args(argv)

    from mongo_bench.config import load_settings
    from mongo_bench.db import get_client

    settings = load_settings()
    client = get_client()
    try:
        ensure_benchmark_collections(
            client,
            settings.mongodb_db,
            skip_search_indexes=True if args.skip_search_indexes else None,
        )
    finally:
        client.close()
    names = bench_collection_names()
    print(f"Benchmark schema applied on database {settings.mongodb_db!r}: {', '.join(names)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
