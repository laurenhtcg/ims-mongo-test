"""Job registries: populate (seed) jobs and benchmark jobs."""

from collections.abc import Callable

from mongo_bench.jobs.benchmarks import search_index, search_atlas, search_wildcard
from mongo_bench.jobs.populate import merge_all, seed_orders, seed_users

PopulateJob = Callable[[], None]
BenchmarkJob = Callable[[], None]

POPULATE_JOBS: dict[str, PopulateJob] = {
    "merge_all": merge_all,
    "seed_users": seed_users,
    "seed_orders": seed_orders,
}

BENCHMARK_JOBS: dict[str, BenchmarkJob] = {
    "search_index": search_index,
    "search_atlas": search_atlas,
    "search_wildcard": search_wildcard,
}

__all__ = [
    "BENCHMARK_JOBS",
    "BenchmarkJob",
    "POPULATE_JOBS",
    "PopulateJob",
]
