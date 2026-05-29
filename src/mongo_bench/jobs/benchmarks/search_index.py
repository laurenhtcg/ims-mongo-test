"""Benchmark ``bench_index`` with compound index ``bench_compound`` and Atlas index ``bench_text``.

Environment (optional):

- ``BENCH_INDEX_COLLECTION`` — default ``bench_index``
- ``BENCH_ATLAS_SEARCH_INDEX`` — default ``bench_text`` (must match ``bench_collections.json``)
- ``BENCH_ATLAS_TEXT_QUERY`` — default ``Dragon``
- ``BENCH_SELLER_KEYS_PER_TIER`` — how many small / large sellers (and some medium); default ``3``
- ``BENCH_USE_STATIC_SELLER_KEYS`` — if ``1`` / ``true`` / ``yes``, use :data:`.benchmark_fixtures.STATIC_BENCH_SELLER_KEYS`
  instead of querying :func:`.benchmark_fixtures.seller_keys_by_volume` (reproducible across benchmark jobs).
- ``BENCH_CSV`` — if ``0`` / ``false`` / ``no``, skip writing a CSV results file (default: write CSV).
- ``BENCH_CSV_PATH`` — if set, exact CSV path (same file each run unless you change it).
- ``BENCH_CSV_DIR`` — when ``BENCH_CSV_PATH`` is unset, CSV is written here (default: current working directory).
- ``BENCH_CSV_UNIQUE`` — if ``0`` / ``false`` / ``no``, use a stable ``{job}_benchmark.csv``; default adds a UTC
  timestamp so each run gets its own file (e.g. ``search_index_benchmark_20260529_153045.csv``).

For each sampled ``sellerKey`` (from volume tiers unless static sellers are enabled), runs a
baseline Atlas compound ``$search`` (``equals`` on ``sellerKey`` + ``text`` on ``product.name``),
then for each :data:`.benchmark_fixtures.FILTER_TESTS` entry (including ``seller_only`` with no
extra dimensions) a timed ``$match`` and the same filter after ``$search``. Each run prints timing
and result count and appends a row to the CSV when enabled.

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

_DEFAULT_COLLECTION = "bench_index"
_DEFAULT_ATLAS_INDEX = "bench_text"
_SEARCH_INDEX_BENCH_JOB = "search_index"

IGNORE_SLUG = "XXXXXX"


def _create_filter(
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
    """Build a ``$match`` filter: always ``sellerKey``; other fields use ``$in`` or a no-op ``$ne`` sentinel.

    Intended for ``_create_filter(seller_key, **params)`` where ``params`` comes from
    :data:`~.benchmark_fixtures.FILTER_TESTS`. Unknown keys raise ``TypeError``; bad value types
    fail when the filter is built or sent to the server.

    When every optional dimension is unset (e.g. ``seller_only`` / ``{}``), returns only
    ``{"sellerKey": seller_key}`` — no ``$ne`` sentinels — matching a plain seller-only ``$match``.
    """
    if (
        not product_line
        and not product_sets
        and not language
        and not printing
        and not rarity
        and not product_types
        and not quantity_min
    ):
        return {"sellerKey": seller_key}

    flt: dict[str, Any] = {"sellerKey": seller_key}

    flt["product.productLine"] = {"$in": product_line} if product_line else {"$ne": IGNORE_SLUG}
    flt["product.set"] = {"$in": product_sets} if product_sets else {"$ne": IGNORE_SLUG}
    flt["product.language"] = {"$in": language} if language else {"$ne": IGNORE_SLUG}
    flt["product.printing"] = {"$in": printing} if printing else {"$ne": IGNORE_SLUG}
    flt["product.rarity"] = {"$in": rarity} if rarity else {"$ne": IGNORE_SLUG}
    flt["product.type"] = {"$in": product_types} if product_types else {"$ne": IGNORE_SLUG}

    if quantity_min:
        flt["inventory.quantity"] = {"$gte": quantity_min}

    return flt


def match_from_filter_test(seller_key: str, params: dict[str, Any]) -> dict[str, Any]:
    """Full ``$match`` document: ``sellerKey`` plus fields from a ``FILTER_TESTS`` param dict."""
    return _create_filter(seller_key, **params)


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


def search_index() -> None:
    """Run benchmark aggregation variants on ``bench_index`` (see module docstring)."""
    from mongo_bench.config import load_settings
    from mongo_bench.db import get_client

    settings = load_settings()
    coll_name = os.environ.get("BENCH_INDEX_COLLECTION", _DEFAULT_COLLECTION)
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
            csv_path = default_benchmark_csv_path(_SEARCH_INDEX_BENCH_JOB)
            try:
                csv_file, csv_writer = open_benchmark_csv(csv_path)
                print(f"mongo-bench: CSV results -> {csv_path!r}")
            except OSError as exc:
                print(f"mongo-bench: could not open CSV {csv_path!r}: {exc}")
                csv_file = None
                csv_writer = None

        print(
            f"bench_index benchmarks  db={settings.mongodb_db!r}  coll={coll_name!r}  "
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
                bench_job=_SEARCH_INDEX_BENCH_JOB,
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
                    bench_job=_SEARCH_INDEX_BENCH_JOB,
                    seller_key=seller_key,
                    tier=tier,
                    csv_writer=csv_writer,
                )
                run_timed_count(
                    coll,
                    [search_stage, {"$match": flt}],
                    f"[{tier}] atlas_plus_match_{test_name}",
                    bench_job=_SEARCH_INDEX_BENCH_JOB,
                    seller_key=seller_key,
                    tier=tier,
                    csv_writer=csv_writer,
                )

        print("bench_index benchmarks finished.")
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
    "IGNORE_SLUG",
    "_create_filter",
    "match_from_filter_test",
    "search_index",
    "seller_keys_by_volume",
]
