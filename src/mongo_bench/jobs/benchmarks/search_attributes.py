"""Benchmark ``bench_attributes`` with compound index ``bench_attributes_compound`` and Atlas index ``bench_text``.

Documents use the attribute pattern: ``attributes`` is an array of ``{ "key", "value" }`` pairs (see
:func:`mongo_bench.jobs.populate.merge_all._add_attributes`). ``$match`` uses ``$elemMatch`` on
``attributes`` so predicates align with the compound index on ``sellerKey``, ``attributes.key``,
``attributes.value``, and ``inventory.quantity``.

Mirrors :mod:`search_wildcard` pipeline shape (optional ``$search`` + sparse ``$match`` + sort/skip/limit).
Case iteration uses :meth:`~.benchmark_session.BenchmarkSession.iter_test_cases`
(:data:`~.benchmark_fixtures.TEST_CASES` × :data:`~.benchmark_fixtures.FILTER_TESTS`).

Environment (optional):

- ``BENCH_ATTRIBUTES_COLLECTION`` — default ``bench_attributes``
- ``BENCH_ATLAS_SEARCH_INDEX`` — default ``bench_text`` (must match ``bench_collections.json`` for this collection)
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
    TEST_CASES,
    bench_skip_limit_stages,
    bench_sort_document,
    seller_keys_by_volume,
)
from .benchmark_session import BenchmarkSession

_DEFAULT_COLLECTION = "bench_attributes"
_DEFAULT_ATLAS_INDEX = "bench_text"
_SEARCH_ATTRIBUTES_BENCH_JOB = "search_attributes"


def _create_attributes_filter(
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
    """Build a sparse ``$match``: ``sellerKey`` plus ``$elemMatch`` only for dimensions that are set.

    Maps :data:`~.benchmark_fixtures.FILTER_TESTS` keys to ``attributes.key`` values used at populate
    time: ``product_line`` → ``productLine``, ``product_sets`` → ``set``, ``product_types`` → ``type``.
    """
    conds: list[dict[str, Any]] = [{"sellerKey": seller_key}]

    def add_pair(attr_key: str, values: list[str] | None) -> None:
        if values:
            conds.append(
                {"attributes": {"$elemMatch": {"key": attr_key, "value": {"$in": values}}}}
            )

    add_pair("productLine", product_line)
    add_pair("set", product_sets)
    add_pair("language", language)
    add_pair("printing", printing)
    add_pair("rarity", rarity)
    add_pair("type", product_types)

    if quantity_min:
        conds.append({"inventory.quantity": {"$gte": quantity_min}})

    if len(conds) == 1:
        return conds[0]
    return {"$and": conds}


def match_from_filter_test(seller_key: str, params: dict[str, Any]) -> dict[str, Any]:
    """Full ``$match`` for attribute-pattern benchmarks: ``sellerKey`` plus ``$elemMatch`` from the test dict."""
    return _create_attributes_filter(seller_key, **params)


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
    """``$search`` (optional) + sparse ``$match`` + optional ``$sort`` / ``$skip`` / ``$limit``.

    Keyword arguments match keys merged by :meth:`~.benchmark_session.BenchmarkSession.iter_test_cases`.
    """
    pipeline: list[dict[str, Any]] = []
    search_text = str(text).strip() if text is not None and str(text).strip() != "" else None
    if search_text:
        pipeline.append(_compound_search_name_stage(atlas_index, seller_key, search_text))
    fp = filters if filters is not None else {}
    pipeline.append({"$match": match_from_filter_test(seller_key, fp)})
    sort_doc = bench_sort_document(sort)
    if sort_doc:
        pipeline.append({"$sort": sort_doc})
    pipeline.extend(bench_skip_limit_stages(skip, limit))
    return pipeline


def search_attributes() -> None:
    """Run benchmark aggregation variants on ``bench_attributes`` (see module docstring)."""
    coll_name = os.environ.get("BENCH_ATTRIBUTES_COLLECTION", _DEFAULT_COLLECTION)
    atlas_index = os.environ.get("BENCH_ATLAS_SEARCH_INDEX", _DEFAULT_ATLAS_INDEX)
    per_tier = int(os.environ.get("BENCH_SELLER_KEYS_PER_TIER", "3"))
    use_static_sellers = os.environ.get("BENCH_USE_STATIC_SELLER_KEYS", "").lower() in (
        "1",
        "true",
        "yes",
    )

    with BenchmarkSession(bench_job=_SEARCH_ATTRIBUTES_BENCH_JOB, coll_name=coll_name) as b:
        sellers = b.seller_sample(per_tier=per_tier, use_static=use_static_sellers)
        if not sellers:
            print(b.empty_collection_hint())
            return

        n_matrix = len(TEST_CASES) * len(FILTER_TESTS)
        print(
            f"bench_attributes benchmarks  db={b.settings.mongodb_db!r}  coll={coll_name!r}  "
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

        print("bench_attributes benchmarks finished.")


__all__ = [
    "FILTER_TESTS",
    "STATIC_BENCH_SELLER_KEYS",
    "TEST_CASES",
    "_create_attributes_filter",
    "match_from_filter_test",
    "search_attributes",
    "seller_keys_by_volume",
]
