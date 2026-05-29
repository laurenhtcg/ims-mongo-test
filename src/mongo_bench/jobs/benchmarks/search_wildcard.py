"""Benchmark ``bench_wildcard`` with compound wildcard index ``bench_wildcard_sellerKey_paths`` and Atlas index ``bench_text``.

Mirrors :mod:`search_index` pipeline shapes; ``$match`` filters only include fields present in each
:data:`~.benchmark_fixtures.FILTER_TESTS` case (no ``$ne`` sentinels) so the wildcard index can serve
dynamic predicates.

Environment (optional):

- ``BENCH_WILDCARD_COLLECTION`` — default ``bench_wildcard``
- ``BENCH_ATLAS_SEARCH_INDEX`` — default ``bench_text`` (must match ``bench_collections.json`` for this collection)
- ``BENCH_ATLAS_TEXT_QUERY`` — default ``Dragon``
- ``BENCH_SELLER_KEYS_PER_TIER`` — default ``3``
- ``BENCH_USE_STATIC_SELLER_KEYS`` — same as :mod:`search_index`
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

_DEFAULT_COLLECTION = "bench_wildcard"
_DEFAULT_ATLAS_INDEX = "bench_text"
_SEARCH_WILDCARD_BENCH_JOB = "search_wildcard"


def _create_wildcard_filter(
    seller_key: str,
    *,
    product_line: list[str] | None = None,
    product_sets: list[str] | None = None,
    language: list[str] | None = None,
    printing: list[str] | None = None,
    rarity: list[str] | None = None,
    product_types: list[str] | None = None,
    quantity_min: int = 0,
) -> dict[str, Any]:
    """Build a sparse ``$match``: ``sellerKey`` plus only dimensions that are set (truthy lists or ``quantity_min``).

    Intended for ``_create_wildcard_filter(seller_key, **params)`` with :data:`~.benchmark_fixtures.FILTER_TESTS`.
    """
    flt: dict[str, Any] = {"sellerKey": seller_key}

    if product_line:
        flt["product.productLine"] = {"$in": product_line}
    if product_sets:
        flt["product.set"] = {"$in": product_sets}
    if language:
        flt["product.language"] = {"$in": language}
    if printing:
        flt["product.printing"] = {"$in": printing}
    if rarity:
        flt["product.rarity"] = {"$in": rarity}
    if product_types:
        flt["product.type"] = {"$in": product_types}
    if quantity_min:
        flt["inventory.quantity"] = {"$gte": quantity_min}

    return flt


def match_from_filter_test(seller_key: str, params: dict[str, Any]) -> dict[str, Any]:
    """Full ``$match`` document for wildcard benchmarks: ``sellerKey`` plus only params from the test dict."""
    return _create_wildcard_filter(seller_key, **params)


def _compound_search_name_stage(atlas_index: str, seller_key: str, text_query: str) -> dict[str, Any]:
    """Atlas ``$search``: ``equals`` on ``sellerKey`` (filter) + ``text`` on ``product.name`` (must)."""
    return {
        "$search": {
            "index": atlas_index,
            "compound": {
                "filter": [{"equals": {"path": "sellerKey", "value": seller_key}}],
                "must": [{"text": {"path": "product.name", "query": text_query}}],
            },
        }
    }


def search_wildcard() -> None:
    """Run benchmark aggregation variants on ``bench_wildcard`` (see module docstring)."""
    from mongo_bench.config import load_settings
    from mongo_bench.db import get_client

    settings = load_settings()
    coll_name = os.environ.get("BENCH_WILDCARD_COLLECTION", _DEFAULT_COLLECTION)
    atlas_index = os.environ.get("BENCH_ATLAS_SEARCH_INDEX", _DEFAULT_ATLAS_INDEX)
    text_query = os.environ.get("BENCH_ATLAS_TEXT_QUERY", "Dragon")
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
            csv_path = default_benchmark_csv_path(_SEARCH_WILDCARD_BENCH_JOB)
            try:
                csv_file, csv_writer = open_benchmark_csv(csv_path)
                print(f"mongo-bench: CSV results -> {csv_path!r}")
            except OSError as exc:
                print(f"mongo-bench: could not open CSV {csv_path!r}: {exc}")
                csv_file = None
                csv_writer = None

        print(
            f"bench_wildcard benchmarks  db={settings.mongodb_db!r}  coll={coll_name!r}  "
            f"atlas_index={atlas_index!r}  text_query={text_query!r}  sellers={len(sellers)}  "
            f"seller_source={'static' if use_static_sellers else 'volume'}  "
            f"filter_tests={len(FILTER_TESTS)}"
        )

        for seller_key, tier in sellers:
            print(f"--- sellerKey={seller_key!r}  tier={tier!r} ---")

            search_stage = _compound_search_name_stage(atlas_index, seller_key, text_query)
            run_timed_count(
                coll,
                [search_stage],
                f"[{tier}] atlas_compound_sellerKey_name",
                bench_job=_SEARCH_WILDCARD_BENCH_JOB,
                seller_key=seller_key,
                tier=tier,
                csv_writer=csv_writer,
            )

            for test_name, test_params in FILTER_TESTS:
                flt = match_from_filter_test(seller_key, test_params)
                run_timed_count(
                    coll,
                    [{"$match": flt}],
                    f"[{tier}] match_{test_name}",
                    bench_job=_SEARCH_WILDCARD_BENCH_JOB,
                    seller_key=seller_key,
                    tier=tier,
                    csv_writer=csv_writer,
                )
                run_timed_count(
                    coll,
                    [search_stage, {"$match": flt}],
                    f"[{tier}] atlas_plus_match_{test_name}",
                    bench_job=_SEARCH_WILDCARD_BENCH_JOB,
                    seller_key=seller_key,
                    tier=tier,
                    csv_writer=csv_writer,
                )

        print("bench_wildcard benchmarks finished.")
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
    "_create_wildcard_filter",
    "match_from_filter_test",
    "search_wildcard",
    "seller_keys_by_volume",
]
