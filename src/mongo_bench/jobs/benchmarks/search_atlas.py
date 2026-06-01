"""Benchmark ``bench_search`` using only Atlas ``$search`` stages (no ``$match`` on the collection).

Uses the same :meth:`~.benchmark_session.BenchmarkSession.iter_test_cases` matrix as
:mod:`search_index` / :mod:`search_wildcard` (one timed pipeline per row, CSV label
``[{tier}] {case_label}``). Each pipeline is a single ``$search`` (``compound`` with facet ``filter``
clauses from ``filters``, optional ``must`` ``text`` on ``product.name`` when ``text`` is set in the
case dict), optional in-search ``sort``, then optional ``$skip`` / ``$limit`` aggregation stages.

Environment (optional):

- ``BENCH_SEARCH_COLLECTION`` — default ``bench_search``
- ``BENCH_SEARCH_ATLAS_INDEX`` — default ``bench_search_index`` (must match ``bench_collections.json``)
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
    TEST_CASES,
    bench_skip_limit_stages,
    bench_sort_document,
    seller_keys_by_volume,
)
from .benchmark_session import BenchmarkSession

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

def _atlas_filter_clauses_from_filter_test_params(
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build Atlas ``compound.filter`` clauses (no ``sellerKey`` here)."""
    clauses: list[dict[str, Any]] = []
    for key, path in _FILTER_PARAM_TO_PATH:
        raw = params.get(key)
        if not raw:
            continue
        clauses.append({"in": {"path": path, "value": raw}})

    qm = params.get("quantity_min", 0) or 0
    if qm > 0:
        clauses.append({"range": {"path": "inventory.quantity", "gte": qm}})

    return clauses


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
    """``$search`` (compound + optional in-search ``sort``) + optional ``$skip`` / ``$limit``.

    Keyword arguments match keys merged by :meth:`~.benchmark_session.BenchmarkSession.iter_test_cases`.
    A ``must`` ``text`` clause is added only when ``text`` is non-blank after strip.
    """
    fp = filters if filters is not None else {}
    tq = str(text).strip() if text is not None and str(text).strip() != "" else ""

    filter_parts: list[dict[str, Any]] = [
        {"equals": {"path": "sellerKey", "value": seller_key}},
    ]
    if fp:
        filter_parts.extend(_atlas_filter_clauses_from_filter_test_params(fp))
    compound: dict[str, Any] = {"filter": filter_parts}
    if tq:
        compound["must"] = [{"text": {"path": "product.name", "query": tq}}]

    body: dict[str, Any] = {"index": atlas_index, "compound": compound}
    sort_doc = bench_sort_document(sort)
    if sort_doc:
        body["sort"] = sort_doc

    stages: list[dict[str, Any]] = [{"$search": body}]
    stages.extend(bench_skip_limit_stages(skip, limit))
    return stages


def search_atlas() -> None:
    """Run Atlas-only search benchmarks on ``bench_search`` (see module docstring)."""
    coll_name = os.environ.get("BENCH_SEARCH_COLLECTION", _DEFAULT_COLLECTION)
    atlas_index = os.environ.get("BENCH_SEARCH_ATLAS_INDEX", _DEFAULT_ATLAS_INDEX)
    per_tier = int(os.environ.get("BENCH_SELLER_KEYS_PER_TIER", "3"))
    use_static_sellers = os.environ.get("BENCH_USE_STATIC_SELLER_KEYS", "").lower() in (
        "1",
        "true",
        "yes",
    )

    with BenchmarkSession(bench_job=_SEARCH_ATLAS_BENCH_JOB, coll_name=coll_name) as b:
        sellers = b.seller_sample(per_tier=per_tier, use_static=use_static_sellers)
        if not sellers:
            print(b.empty_collection_hint())
            return

        n_matrix = len(TEST_CASES) * len(FILTER_TESTS)
        print(
            f"bench_search (atlas-only)  db={b.settings.mongodb_db!r}  coll={coll_name!r}  "
            f"atlas_index={atlas_index!r}  sellers={len(sellers)}  "
            f"seller_source={'static' if use_static_sellers else 'volume'}  "
            f"cases={n_matrix}  (same matrix as search_index / search_wildcard)"
        )

        for tier, seller_key, case_label, params in b.iter_test_cases(sellers):
            pipeline = _create_pipeline(atlas_index, seller_key, **params)
            b.timed(
                pipeline,
                f"[{tier}] {case_label}",
                seller_key=seller_key,
                tier=tier,
            )

        print("bench_search (atlas-only) benchmarks finished.")


__all__ = [
    "FILTER_TESTS",
    "STATIC_BENCH_SELLER_KEYS",
    "TEST_CASES",
    "_atlas_filter_clauses_from_filter_test_params",
    "_create_pipeline",
    "search_atlas",
    "seller_keys_by_volume",
]
