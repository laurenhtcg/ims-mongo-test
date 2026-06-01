"""Shared benchmark run lifecycle: Mongo client, collection, optional CSV, teardown.

Use :class:`BenchmarkSession` as a context manager so each benchmark job only supplies
collection name, seller sampling, and pipeline construction (per seller / filter test).
"""

from __future__ import annotations

import csv
import os
import sys
import time
from typing import Any, Iterator, TextIO

from .benchmark_fixtures import (
    TEST_CASES,
    FILTER_TESTS,
    STATIC_BENCH_SELLER_KEYS,
    bench_csv_enabled,
    default_benchmark_csv_path,
    open_benchmark_csv,
    seller_keys_by_volume,
)


class BenchmarkSession:
    """Context manager: open DB connection, optional results CSV, timed aggregation + count.

    On exit, closes the CSV file (if opened) and the Mongo client. Import ``mongo_bench.db`` only
    inside :meth:`__enter__` to match lazy-import style used by benchmark entrypoints.

    Parameters
    ----------
    bench_job
        Logical job name (CSV stem and ``bench_job`` column).
    coll_name
        Collection name within the configured database.
    """

    def __init__(self, *, bench_job: str, coll_name: str) -> None:
        self.bench_job = bench_job
        self.coll_name = coll_name
        self._settings: Any = None
        self._client: Any = None
        self.coll: Any = None
        self.csv_file: TextIO | None = None
        self.csv_writer: csv.DictWriter | None = None
        self.csv_path: str | None = None

    @property
    def settings(self) -> Any:
        """Settings from :func:`mongo_bench.config.load_settings` (set after :meth:`__enter__`)."""
        return self._settings

    def __enter__(self) -> BenchmarkSession:
        from mongo_bench.config import load_settings
        from mongo_bench.db import get_client

        self._settings = load_settings()
        self._client = get_client()
        self.coll = self._client[self._settings.mongodb_db][self.coll_name]

        if bench_csv_enabled():
            self.csv_path = default_benchmark_csv_path(self.bench_job)
            try:
                self.csv_file, self.csv_writer = open_benchmark_csv(self.csv_path)
                print(f"mongo-bench: CSV results -> {self.csv_path!r}")
            except OSError as exc:
                print(f"mongo-bench: could not open CSV {self.csv_path!r}: {exc}")
                self.csv_file = None
                self.csv_writer = None

        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> bool | None:
        if self.csv_file is not None:
            try:
                self.csv_file.close()
            except OSError:
                pass
            self.csv_file = None
            self.csv_writer = None
        if self._client is not None:
            self._client.close()
            self._client = None
        self.coll = None
        self._settings = None
        return False

    def seller_sample(
        self,
        *,
        per_tier: int | None = None,
        use_static: bool | None = None,
    ) -> list[tuple[str, str]]:
        """Return seller keys for the run (static list or :func:`seller_keys_by_volume` on :attr:`coll`).

        When ``use_static`` / ``per_tier`` are omitted, values are taken from the environment (same
        defaults as the benchmark CLI).
        """
        if use_static is None:
            use_static = os.environ.get("BENCH_USE_STATIC_SELLER_KEYS", "").lower() in (
                "1",
                "true",
                "yes",
            )
        if per_tier is None:
            per_tier = int(os.environ.get("BENCH_SELLER_KEYS_PER_TIER", "3"))
        if use_static:
            keys = list(STATIC_BENCH_SELLER_KEYS)
            if keys and self.coll is not None:
                probe_key = keys[0][0]
                if self.coll.count_documents({"sellerKey": probe_key}, limit=1) == 0:
                    print(
                        "mongo-bench: WARNING: static sellerKey "
                        f"{probe_key!r} matches no documents in "
                        f"{self._settings.mongodb_db!r}.{self.coll_name!r}. "
                        "Benchmarks will report count=0 until keys align with this collection. "
                        "Unset BENCH_USE_STATIC_SELLER_KEYS to sample real keys, or run "
                        "`mongo-bench list-seller-keys` and update "
                        "benchmark_fixtures.STATIC_BENCH_SELLER_KEYS.",
                        file=sys.stderr,
                    )
            return keys
        return seller_keys_by_volume(self.coll, per_tier=per_tier)

    def empty_collection_hint(self) -> str:
        """Message when :meth:`seller_sample` is empty (collection missing or empty)."""
        return (
            f"mongo-bench: no documents in {self._settings.mongodb_db!r}.{self.coll_name!r}; "
            "populate first."
        )

    def iter_test_cases(
        self,
        sellers: list[tuple[str, str]] | None = None,
    ) -> Iterator[tuple[str, str, str, dict[str, Any]]]:
        """Yield ``(tier, seller_key, case_label, params)``.

        ``sellers`` must be ``(sellerKey, tier)`` tuples, matching :data:`~.benchmark_fixtures.STATIC_BENCH_SELLER_KEYS`
        and :func:`~.benchmark_fixtures.seller_keys_by_volume`.

        ``params`` is ``{**test_case_params, "filters": <FILTER_TESTS dict>}`` so each row carries
        search/sort/pagination knobs from :data:`~.benchmark_fixtures.TEST_CASES` plus facet filters
        under the string key ``"filters"``.

        ``case_label`` is ``"{test_name}_{filter_name}"`` for logs/CSV.

        Pass ``sellers`` from a prior :meth:`seller_sample` call to avoid sampling twice.
        """
        if sellers is None:
            sellers = self.seller_sample()
        for seller_key, tier in sellers:
            for test_name, test_params in TEST_CASES:
                for filter_name, filters in FILTER_TESTS:
                    case_label = f"{test_name}_{filter_name}"
                    yield tier, seller_key, case_label, {**test_params, "filters": filters or {}}

    def timed(
        self,
        pipeline: list[dict[str, Any]],
        label: str,
        *,
        seller_key: str,
        tier: str,
    ) -> float:
        """Run ``pipeline`` + ``$count`` on :attr:`coll`; print ms and count; optional CSV row."""
        coll = self.coll
        csv_writer = self.csv_writer
        bench_job = self.bench_job
        full = [*pipeline, {"$count": "c"}]
        t0 = time.perf_counter()
        try:
            rows = list(coll.aggregate(full, allowDiskUse=True))
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            print(f"{label}: FAILED: {exc}")
            if csv_writer is not None:
                csv_writer.writerow(
                    {
                        "bench_job": bench_job,
                        "collection": coll.name,
                        "tier": tier,
                        "seller_key": seller_key,
                        "label": label,
                        "elapsed_ms": f"{elapsed_ms:.4f}",
                        "count": "-1",
                        "error": str(exc),
                    }
                )
            return -1.0
        elapsed = time.perf_counter() - t0
        elapsed_ms = elapsed * 1000.0
        n = int(rows[0]["c"]) if rows else 0
        print(f"{label}: {elapsed_ms:.2f} ms  count={n}")
        if csv_writer is not None:
            csv_writer.writerow(
                {
                    "bench_job": bench_job,
                    "collection": coll.name,
                    "tier": tier,
                    "seller_key": seller_key,
                    "label": label,
                    "elapsed_ms": f"{elapsed_ms:.4f}",
                    "count": str(n),
                    "error": "",
                }
            )
        return elapsed


__all__ = ["BenchmarkSession"]
