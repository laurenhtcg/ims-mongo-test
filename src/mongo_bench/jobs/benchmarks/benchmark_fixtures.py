"""Shared benchmark inputs used across jobs in this package.

Holds cross-benchmark data such as :data:`FILTER_TESTS`, :data:`STATIC_BENCH_SELLER_KEYS`, and
:func:`seller_keys_by_volume`. Timed aggregation + CSV rows are implemented by
:meth:`~.benchmark_session.BenchmarkSession.timed`. Use :class:`~.benchmark_session.BenchmarkSession`
for client/CSV/teardown around each job. Filter construction for ``bench_index`` / ``search_index`` lives
in :mod:`search_index`; sparse filters for ``search_wildcard`` in :mod:`search_wildcard`;
attribute-pattern ``$elemMatch`` filters for ``search_attributes`` in :mod:`search_attributes`; Atlas-only
clauses for ``search_atlas`` in :mod:`search_atlas`.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from typing import Any, TextIO

TEST_CASES = [
    ("filters_only", {}),
    ("filters_and_deep_pagination", {"sort": "name", "skip": 1000, "limit": 100}),
    ("search", {"text": "Dragon"}),
    ("search_and_sort_quantity", {"text": "Dragon", "sort": "quantity"}),
    ("search_and_pagination", {"text": "Dragon", "sort": "name", "skip": 10, "limit": 10}),
    ("search_and_deep_pagination", {"text": "Dragon", "sort": "name", "skip": 1000, "limit": 100}),
]

# Each entry is ``("test name", filter param dict)`` for ``search_index`` / ``search_wildcard`` /
# ``search_attributes`` / ``search_atlas`` (Atlas-only uses the same param dicts as ``in`` / ``range``
# inside ``$search``).
FILTER_TESTS: list[tuple[str, dict[str, Any]]] = [
    (
        "no_filters",
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
        "line_and_rarity",
        {
            "product_line": ["Magic The Gathering TCG"],
            "rarity": ["Common", "Rare"],
        },
    ),
    (
        "line_and_languages",
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
        "rare_product_line",
        {
            "product_line": ["Warhammer Age of Sigmar Champions TCG"]
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


def _bench_nonneg_int(value: Any) -> int:
    """Coerce ``value`` to a non-negative int; booleans and invalid values become ``0``."""
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float) and value == int(value):
        return max(0, int(value))
    try:
        return max(0, int(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def bench_sort_document(sort: Any) -> dict[str, int] | None:
    """Document for aggregation ``$sort`` or Atlas ``$search`` ``sort`` (ascending).

    ``TEST_CASES`` use ``sort`` values ``name`` → ``product.name``, ``quantity`` →
    ``inventory.quantity``.
    """
    if not isinstance(sort, str):
        return None
    key = sort.strip().lower()
    if key == "name":
        return {"product.name": 1}
    if key == "quantity":
        return {"inventory.quantity": 1}
    return None


def bench_skip_limit_stages(skip: Any, limit: Any) -> list[dict[str, Any]]:
    """Build ``$skip`` / ``$limit`` stages from ``TEST_CASES`` ``skip`` / ``limit`` keys.

    Stages are omitted when the coerced value is ``0``. ``$skip`` precedes ``$limit`` when both are set.
    """
    out: list[dict[str, Any]] = []
    sk = _bench_nonneg_int(skip)
    if sk > 0:
        out.append({"$skip": sk})
    lm = _bench_nonneg_int(limit)
    if lm > 0:
        out.append({"$limit": lm})
    return out


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
    "TEST_CASES",
    "bench_skip_limit_stages",
    "bench_sort_document",
    "bench_csv_enabled",
    "bench_csv_unique_enabled",
    "default_benchmark_csv_path",
    "open_benchmark_csv",
    "seller_keys_by_volume",
]
