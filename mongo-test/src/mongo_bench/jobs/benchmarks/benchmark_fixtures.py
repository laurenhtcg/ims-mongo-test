"""Shared benchmark inputs used across jobs in this package.

Holds cross-benchmark data such as :data:`FILTER_TESTS`, :data:`STATIC_BENCH_SELLER_KEYS`,
:func:`seller_keys_by_volume`, and :func:`run_timed_count` for timed aggregation + CSV logging (per
benchmark job name and per-run timestamps by default). Filter construction for ``bench_index`` /
``search_index`` lives in :mod:`search_index`; sparse filters for ``search_wildcard`` in
:mod:`search_wildcard`; Atlas-only clauses for ``search_atlas`` in :mod:`search_atlas`.
"""

from __future__ import annotations

import csv
import os
import time
from datetime import datetime, timezone
from typing import Any, TextIO

# Each entry is ``("test name", filter param dict)`` for ``search_index`` / ``search_wildcard`` /
# ``search_atlas`` (Atlas-only uses the same param dicts as ``in`` / ``range`` inside ``$search``).
FILTER_TESTS: list[tuple[str, dict[str, Any]]] = [
    (
        "seller_only",
        {},
    ),
    (
        "multiple_filters_mtg",
        {
            "product_line": ["Magic The Gathering TCG"],
            "product_sets": ["Commander Legends", "Aetherspiral"],
            "language": ["English"],
            "printing": ["Normal"],
        },
    ),
    (
        "multiple_filters_pkm",
        {
            "product_line": ["Pokémon TCG"],
            "product_sets": [
                "League & Championship Cards",
                "SWSH01: Sword & Shield Base Set",
            ],
            "language": ["English"],
            "printing": ["Holofoil"],
        },
    ),
    (
        "sparse_filters",
        {
            "product_line": ["Magic The Gathering TCG"],
            "rarity": ["Common", "Rare"],
        },
    ),
    (
        "multiple_languages",
        {
            "product_line": ["Magic The Gathering TCG"],
            "language": ["English", "Japanese"],
            "printing": ["Normal"],
        },
    ),
    (
        "product_line_only",
        {
            "product_line": ["Magic The Gathering TCG"],
        },
    ),
    (
        "product_line_with_quantity",
        {
            "product_line": ["Magic The Gathering TCG"],
            "quantity_min": 10,
        },
    ),
    (
        "rare_product_lines",
        {
            "product_line": ["Union Arena", "Argent Saga TCG", "Warhammer Age of Sigmar Champions TCG"]
        },
    ),
]

# ``(sellerKey, tier)`` for reproducible benchmarks when ``BENCH_USE_STATIC_SELLER_KEYS`` is set.
# Regenerate from your data: ``mongo-bench list-seller-keys`` (uses :func:`seller_keys_by_volume` on
# ``BENCH_INDEX_COLLECTION`` / ``bench_index`` by default; see ``--help``).
# Keys may not exist if your dataset differs.
STATIC_BENCH_SELLER_KEYS: list[tuple[str, str]] = [
    ("3617b942", "small"),
    ("0750c1d5", "small"),
    ("14efc4dc", "small"),
    ("2413638f", "large"),
    ("1a5d3927", "large"),
    ("3da9b755", "large"),
    ("05bdfca5", "medium"),
    ("3b1bc6ed", "medium"),
    ("14d1f560", "medium"),
]

BENCHMARK_CSV_COLUMNS: tuple[str, ...] = (
    "bench_job",
    "collection",
    "tier",
    "seller_key",
    "label",
    "elapsed_ms",
    "count",
    "error",
)


def bench_csv_enabled() -> bool:
    """Return whether CSV logging is on (default yes; set ``BENCH_CSV=0`` / ``false`` / ``no`` to disable)."""
    return os.environ.get("BENCH_CSV", "1").lower() not in ("0", "false", "no")


def bench_csv_unique_enabled() -> bool:
    """If true (default), auto-generated CSV paths include a UTC timestamp so each run gets its own file."""
    return os.environ.get("BENCH_CSV_UNIQUE", "1").lower() not in ("0", "false", "no")


def default_benchmark_csv_path(bench_job: str) -> str:
    """Resolve CSV path for this benchmark *run*.

    - If ``BENCH_CSV_PATH`` is set, that path is used exactly (same file every run unless you change it).
    - Otherwise the file is ``{bench_job}_benchmark_{utc_timestamp}.csv`` under ``BENCH_CSV_DIR`` (cwd
      when unset). Set ``BENCH_CSV_UNIQUE=0`` for a stable ``{bench_job}_benchmark.csv`` (overwrites
      each run).
    """
    explicit = os.environ.get("BENCH_CSV_PATH")
    if explicit:
        return explicit
    out_dir = os.environ.get("BENCH_CSV_DIR", "").strip()
    if bench_csv_unique_enabled():
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base = f"{bench_job}_benchmark_{ts}.csv"
    else:
        base = f"{bench_job}_benchmark.csv"
    if not out_dir:
        return base
    return os.path.join(out_dir, base)


def open_benchmark_csv(path: str) -> tuple[TextIO, csv.DictWriter]:
    """Open ``path`` for write and return ``(file, DictWriter)`` with header written."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    f: TextIO = open(path, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=list(BENCHMARK_CSV_COLUMNS))
    w.writeheader()
    return f, w


def run_timed_count(
    coll: Any,
    pipeline: list[dict[str, Any]],
    label: str,
    *,
    bench_job: str = "",
    seller_key: str = "",
    tier: str = "",
    csv_writer: csv.DictWriter | None = None,
) -> float:
    """Run ``pipeline`` + ``$count``; print ms and count; optionally append one CSV row."""
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


def seller_keys_by_volume(coll: Any, *, per_tier: int) -> list[tuple[str, str]]:
    """Return ``(sellerKey, tier)`` for small / large / medium sellers by document count."""
    grouped = list(
        coll.aggregate(
            [
                {"$group": {"_id": "$sellerKey", "n": {"$sum": 1}}},
                {"$sort": {"n": 1}},
            ],
            allowDiskUse=True,
        )
    )
    if not grouped:
        return []

    out: list[tuple[str, str]] = []
    n = max(1, min(per_tier, len(grouped)))
    for doc in grouped[:n]:
        out.append((str(doc["_id"]), "small"))
    for doc in grouped[-n:]:
        out.append((str(doc["_id"]), "large"))
    mid = len(grouped) // 2
    span = max(1, n // 2 or 1)
    for doc in grouped[max(0, mid - span) : min(len(grouped), mid + span + 1)]:
        key = str(doc["_id"])
        if all(k != key for k, _ in out):
            out.append((key, "medium"))
    return out[: max(3, n * 3)]


__all__ = [
    "BENCHMARK_CSV_COLUMNS",
    "FILTER_TESTS",
    "STATIC_BENCH_SELLER_KEYS",
    "bench_csv_enabled",
    "bench_csv_unique_enabled",
    "default_benchmark_csv_path",
    "open_benchmark_csv",
    "run_timed_count",
    "seller_keys_by_volume",
]
