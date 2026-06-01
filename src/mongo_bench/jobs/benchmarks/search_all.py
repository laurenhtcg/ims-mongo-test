"""Run every registered search benchmark in one CLI invocation (``mongo-bench bench search_all``).

Executes, in order:

1. :func:`search_index.search_index` — ``bench_index``
2. :func:`search_atlas.search_atlas` — ``bench_search`` (Atlas-only)
3. :func:`search_attributes.search_attributes` — ``bench_attributes``
4. :func:`search_wildcard.search_wildcard` — ``bench_wildcard``

Each job reads the same environment variables as when run alone (per-job collection overrides, CSV
paths, seller sampling, etc.). CSV output remains **per job** (distinct ``bench_job`` column and
default filenames).

When adding a new search benchmark module, append it to :data:`_SEARCH_BENCHMARK_ORDER` and register
the job in ``mongo_bench.jobs.BENCHMARK_JOBS``.
"""

from __future__ import annotations

from collections.abc import Callable

from mongo_bench.jobs.benchmarks.search_atlas import search_atlas
from mongo_bench.jobs.benchmarks.search_attributes import search_attributes
from mongo_bench.jobs.benchmarks.search_index import search_index
from mongo_bench.jobs.benchmarks.search_wildcard import search_wildcard

_SEARCH_BENCHMARK_ORDER: tuple[tuple[str, Callable[[], None]], ...] = (
    ("search_index", search_index),
    ("search_atlas", search_atlas),
    ("search_attributes", search_attributes),
    ("search_wildcard", search_wildcard),
)


def search_all() -> None:
    """Run each search benchmark job in :data:`_SEARCH_BENCHMARK_ORDER`."""
    print(
        f"mongo-bench search_all: running {len(_SEARCH_BENCHMARK_ORDER)} benchmark jobs "
        f"({', '.join(n for n, _ in _SEARCH_BENCHMARK_ORDER)})."
    )
    for name, run in _SEARCH_BENCHMARK_ORDER:
        print(f"\n--- search_all: {name!r} ---\n")
        run()
    print("\nsearch_all: all benchmark jobs finished.")


__all__ = ["_SEARCH_BENCHMARK_ORDER", "search_all"]
