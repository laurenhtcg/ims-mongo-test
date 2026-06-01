"""Job registries: populate (seed) jobs and benchmark jobs."""

from collections.abc import Callable

from mongo_bench.jobs.benchmarks.search_all import search_all
from mongo_bench.jobs.benchmarks.search_atlas import search_atlas
from mongo_bench.jobs.benchmarks.search_attributes import search_attributes
from mongo_bench.jobs.benchmarks.search_index import search_index
from mongo_bench.jobs.benchmarks.search_wildcard import search_wildcard
from mongo_bench.jobs.populate import merge_all

PopulateJob = Callable[[], None]
BenchmarkJob = Callable[[], None]

POPULATE_JOBS: dict[str, PopulateJob] = {
    "merge_all": merge_all,
}

BENCHMARK_JOBS: dict[str, BenchmarkJob] = {
    "search_index": search_index,
    "search_atlas": search_atlas,
    "search_attributes": search_attributes,
    "search_wildcard": search_wildcard,
    "search_all": search_all,
}

__all__ = [
    "BENCHMARK_JOBS",
    "BenchmarkJob",
    "POPULATE_JOBS",
    "PopulateJob",
]
