"""Benchmark ``bench_index`` with compound index ``bench_compound`` and Atlas index ``bench_text``.

Environment (optional):

- ``BENCH_INDEX_COLLECTION`` — default ``bench_index``
- ``BENCH_ATLAS_SEARCH_INDEX`` — default ``bench_text`` (must match ``bench_collections.json``)
- ``BENCH_SELLER_KEYS_PER_TIER`` — how many small / large sellers (and some medium); default ``3``
- ``BENCH_USE_STATIC_SELLER_KEYS`` — if ``1`` / ``true`` / ``yes``, use :data:`.benchmark_fixtures.STATIC_BENCH_SELLER_KEYS`
  instead of querying :func:`.benchmark_fixtures.seller_keys_by_volume` (reproducible across benchmark jobs).
- ``BENCH_CSV`` — if ``0`` / ``false`` / ``no``, skip writing a CSV results file (default: write CSV).
- ``BENCH_CSV_PATH`` — if set, exact CSV path (same file each run unless you change it).
- ``BENCH_CSV_DIR`` — when ``BENCH_CSV_PATH`` is unset, CSV is written here (default: current working directory).
- ``BENCH_CSV_UNIQUE`` — if ``0`` / ``false`` / ``no``, use a stable ``{job}_benchmark.csv``; default adds a UTC
  timestamp so each run gets its own file (e.g. ``search_index_benchmark_20260529_153045.csv``).

For each sampled ``sellerKey``, runs the Cartesian product of :data:`.benchmark_fixtures.TEST_CASES`
and :data:`.benchmark_fixtures.FILTER_TESTS`: optional Atlas ``$search`` on ``product.name`` (when the
case includes ``text``), ``$match`` from ``filters``, then optional ``$sort`` / ``$skip`` / ``$limit``
from :func:`.benchmark_fixtures.bench_sort_document` and :func:`.benchmark_fixtures.bench_skip_limit_stages`.

Re-apply Atlas search indexes after changing ``bench_collections.json``.
"""

from __future__ import annotations

import os
from typing import Any

from .benchmark_fixtures import (
    FILTER_TESTS,
    STATIC_BENCH_SELLER_KEYS,
    TEST_CASES,
    bench_skip_limit_stages,
    bench_sort_document,
    seller_keys_by_volume,
)
from .benchmark_session import BenchmarkSession

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


def _create_pipeline(
    atlas_index: str,
    seller_key: str,
    *,
    text: Any = None,
    sort: Any = None,
    skip: Any = None,
    limit: Any = None,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """``$search`` (optional) + ``$match`` + optional ``$sort`` / ``$skip`` / ``$limit``.

    Keyword arguments match keys merged by :meth:`~.benchmark_session.BenchmarkSession.iter_test_cases`.
    """
    pipeline: list[dict[str, Any]] = []
    search_text = str(text).strip() if text is not None and str(text).strip() != "" else None
    if search_text:
        pipeline.append(_compound_search_name_stage(atlas_index, seller_key, search_text))
    fp = filters if filters is not None else {}
    pipeline.append({"$match": _create_filter(seller_key, **fp)})
    sort_doc = bench_sort_document(sort)
    if sort_doc:
        pipeline.append({"$sort": sort_doc})
    pipeline.extend(bench_skip_limit_stages(skip, limit))
    return pipeline


def search_index() -> None:
    """Run benchmark aggregation variants on ``bench_index`` (see module docstring)."""
    coll_name = os.environ.get("BENCH_INDEX_COLLECTION", _DEFAULT_COLLECTION)
    atlas_index = os.environ.get("BENCH_ATLAS_SEARCH_INDEX", _DEFAULT_ATLAS_INDEX)
    per_tier = int(os.environ.get("BENCH_SELLER_KEYS_PER_TIER", "3"))
    use_static_sellers = os.environ.get("BENCH_USE_STATIC_SELLER_KEYS", "").lower() in (
        "1",
        "true",
        "yes",
    )

    with BenchmarkSession(bench_job=_SEARCH_INDEX_BENCH_JOB, coll_name=coll_name) as b:
        sellers = b.seller_sample(per_tier=per_tier, use_static=use_static_sellers)
        if not sellers:
            print(b.empty_collection_hint())
            return

        n_matrix = len(TEST_CASES) * len(FILTER_TESTS)
        print(
            f"bench_index benchmarks  db={b.settings.mongodb_db!r}  coll={coll_name!r}  "
            f"atlas_index={atlas_index!r}  sellers={len(sellers)}  "
            f"seller_source={'static' if use_static_sellers else 'volume'}  "
            f"cases={n_matrix}  (TEST_CASES × FILTER_TESTS)"
        )

        for tier, seller_key, case_label, params in b.iter_test_cases(sellers):
            pipeline = _create_pipeline(atlas_index, seller_key, **params)
            b.timed(
                pipeline,
                f"[{tier}] {case_label}",
                seller_key=seller_key,
                tier=tier,
            )

        print("bench_index benchmarks finished.")


__all__ = [
    "FILTER_TESTS",
    "STATIC_BENCH_SELLER_KEYS",
    "TEST_CASES",
    "IGNORE_SLUG",
    "_create_filter",
    "match_from_filter_test",
    "search_index",
    "seller_keys_by_volume",
]
