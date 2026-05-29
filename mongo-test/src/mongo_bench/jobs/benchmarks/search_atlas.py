"""Benchmark ``bench_search`` using only Atlas ``$search`` stages (no ``$match`` on the collection).

Mirrors :mod:`search_index` / :mod:`search_wildcard` **per seller**: for each
:data:`~.benchmark_fixtures.FILTER_TESTS` entry (including ``seller_only`` / ``{}``) two pipelines —
``include_text=False`` (facet filters in Atlas only, like ``match_*``) and ``include_text=True`` (same
filters plus ``must`` ``text`` on ``product.name``, like ``atlas_plus_match_*``). The
``include_text`` flag is passed **per call** to :func:`_compound_search_atlas_stage`, not as a global
benchmark mode.

Environment (optional):

- ``BENCH_SEARCH_COLLECTION`` — default ``bench_search``
- ``BENCH_SEARCH_ATLAS_INDEX`` — default ``bench_search_dynamic_all`` (must match ``bench_collections.json``)
- ``BENCH_ATLAS_TEXT_QUERY`` — string for the name ``text`` clause when ``include_text=True``; default ``Dragon``
- ``BENCH_SELLER_KEYS_PER_TIER`` — default ``3``
- ``BENCH_USE_STATIC_SELLER_KEYS`` — same as other search benchmarks
- ``BENCH_CSV`` / ``BENCH_CSV_PATH`` / ``BENCH_CSV_DIR`` / ``BENCH_CSV_UNIQUE`` — same as :mod:`search_index`

Re-apply Atlas search indexes after changing ``bench_collections.json``.
"""

from __future__ import annotations

import os
from typing import Any

from .benchmark_fixtures import (
    FILTER_TESTS,
    STATIC_BENCH_SELLER_KEYS,
    bench_csv_enabled,
    default_benchmark_csv_path,
    open_benchmark_csv,
    run_timed_count,
    seller_keys_by_volume,
)

_DEFAULT_COLLECTION = "bench_search"
_DEFAULT_ATLAS_INDEX = "bench_search_index"
_SEARCH_ATLAS_BENCH_JOB = "search_atlas"

# FILTER_TESTS dict keys -> Atlas field paths for ``in`` queries.
_FILTER_PARAM_TO_PATH: tuple[tuple[str, str], ...] = (
    ("product_line", "product.productLine"),
    ("product_sets", "product.set"),
    ("language", "product.language"),
    ("printing", "product.printing"),
    ("rarity", "product.rarity"),
    ("product_types", "product.type"),
)


def _quantity_min_int(params: dict[str, Any]) -> int:
    v = params.get("quantity_min", 0)
    if isinstance(v, bool) or v is None:
        return 0
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v == int(v):
        return int(v)
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _atlas_filter_clauses_from_filter_test_params(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Build Atlas ``compound.filter`` clauses (no ``sellerKey`` here)."""
    clauses: list[dict[str, Any]] = []
    for key, path in _FILTER_PARAM_TO_PATH:
        raw = params.get(key)
        if not raw:
            continue
        if isinstance(raw, list):
            vals = [str(x) for x in raw if x is not None and str(x) != ""]
            if vals:
                clauses.append({"in": {"path": path, "value": vals}})
        else:
            clauses.append({"in": {"path": path, "value": [str(raw)]}})
    qm = _quantity_min_int(params)
    if qm > 0:
        clauses.append({"range": {"path": "inventory.quantity", "gte": qm}})
    return clauses


def _compound_search_atlas_stage(
    atlas_index: str,
    seller_key: str,
    text_query: str,
    *,
    include_text: bool = False,
    filter_test_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single ``$search`` compound: ``sellerKey`` + optional FILTER_TESTS dimensions; optional ``text`` on ``product.name``.

    When ``include_text`` is true and ``text_query`` is non-blank after strip, adds ``compound.must``
    with a ``text`` operator on ``product.name``. Otherwise the compound has only ``filter`` (facet-style
    Atlas, comparable to Mongo ``$match`` without a name keyword).
    """
    filter_parts: list[dict[str, Any]] = [
        {"equals": {"path": "sellerKey", "value": seller_key}},
    ]
    if filter_test_params:
        filter_parts.extend(_atlas_filter_clauses_from_filter_test_params(filter_test_params))
    compound: dict[str, Any] = {"filter": filter_parts}
    tq = (text_query or "").strip()
    if include_text and tq:
        compound["must"] = [{"text": {"path": "product.name", "query": tq}}]
    return {
        "$search": {
            "index": atlas_index,
            "compound": compound,
        }
    }


def search_atlas() -> None:
    """Run Atlas-only search benchmarks on ``bench_search`` (see module docstring)."""
    from mongo_bench.config import load_settings
    from mongo_bench.db import get_client

    settings = load_settings()
    coll_name = os.environ.get("BENCH_SEARCH_COLLECTION", _DEFAULT_COLLECTION)
    atlas_index = os.environ.get("BENCH_SEARCH_ATLAS_INDEX", _DEFAULT_ATLAS_INDEX)
    text_query = os.environ.get("BENCH_ATLAS_TEXT_QUERY", "Dragon").strip()
    per_tier = int(os.environ.get("BENCH_SELLER_KEYS_PER_TIER", "3"))
    use_static_sellers = os.environ.get("BENCH_USE_STATIC_SELLER_KEYS", "").lower() in (
        "1",
        "true",
        "yes",
    )

    client = get_client()
    csv_file = None
    csv_writer = None
    csv_path: str | None = None
    try:
        coll = client[settings.mongodb_db][coll_name]

        sellers = (
            list(STATIC_BENCH_SELLER_KEYS)
            if use_static_sellers
            else seller_keys_by_volume(coll, per_tier=per_tier)
        )
        if not sellers:
            print(f"mongo-bench: no documents in {settings.mongodb_db!r}.{coll_name!r}; populate first.")
            return

        if bench_csv_enabled():
            csv_path = default_benchmark_csv_path(_SEARCH_ATLAS_BENCH_JOB)
            try:
                csv_file, csv_writer = open_benchmark_csv(csv_path)
                print(f"mongo-bench: CSV results -> {csv_path!r}")
            except OSError as exc:
                print(f"mongo-bench: could not open CSV {csv_path!r}: {exc}")
                csv_file = None
                csv_writer = None

        print(
            f"bench_search (atlas-only)  db={settings.mongodb_db!r}  coll={coll_name!r}  "
            f"atlas_index={atlas_index!r}  text_query={text_query!r}  sellers={len(sellers)}  "
            f"seller_source={'static' if use_static_sellers else 'volume'}  "
            f"filter_tests={len(FILTER_TESTS)}  (per test: atlas_only_* then atlas_plus_text_*)"
        )

        for seller_key, tier in sellers:
            print(f"--- sellerKey={seller_key!r}  tier={tier!r} ---")

            for test_name, test_params in FILTER_TESTS:
                # Mirrors match_{test_name} — facet filters in Atlas only (no name text).
                run_timed_count(
                    coll,
                    [
                        _compound_search_atlas_stage(
                            atlas_index,
                            seller_key,
                            text_query,
                            include_text=False,
                            filter_test_params=test_params,
                        )
                    ],
                    f"[{tier}] atlas_only_{test_name}",
                    bench_job=_SEARCH_ATLAS_BENCH_JOB,
                    seller_key=seller_key,
                    tier=tier,
                    csv_writer=csv_writer,
                )
                # Mirrors atlas_plus_match_{test_name} — facet filters + name text in one $search.
                run_timed_count(
                    coll,
                    [
                        _compound_search_atlas_stage(
                            atlas_index,
                            seller_key,
                            text_query,
                            include_text=True,
                            filter_test_params=test_params,
                        )
                    ],
                    f"[{tier}] atlas_plus_text_{test_name}",
                    bench_job=_SEARCH_ATLAS_BENCH_JOB,
                    seller_key=seller_key,
                    tier=tier,
                    csv_writer=csv_writer,
                )

        print("bench_search (atlas-only) benchmarks finished.")
    finally:
        if csv_file is not None:
            try:
                csv_file.close()
            except OSError:
                pass
        client.close()


__all__ = [
    "FILTER_TESTS",
    "STATIC_BENCH_SELLER_KEYS",
    "_atlas_filter_clauses_from_filter_test_params",
    "_compound_search_atlas_stage",
    "search_atlas",
    "seller_keys_by_volume",
]
