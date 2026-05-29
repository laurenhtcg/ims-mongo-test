#!/usr/bin/env python3
"""Regenerate bench-pipelines/*.md with aggregation pipeline JSON from benchmark code.

Run from repo root::

    PYTHONPATH=src python3 docs/bench-pipelines/generate_pipeline_docs.py

Uses the same helpers as :mod:`mongo_bench.jobs.benchmarks.search_index`, etc.
"""

from __future__ import annotations

import importlib
import json
import textwrap
from pathlib import Path

from mongo_bench.jobs.benchmarks.benchmark_fixtures import FILTER_TESTS

SK = "<SELLER_KEY>"
IDX_TEXT = "bench_text"
IDX_SEARCH = "bench_search_index"
TQ = "Dragon"


def _load(name: str):
    return importlib.import_module(f"mongo_bench.jobs.benchmarks.{name}")


def dumps(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def header(title: str, coll: str, job: str, extra: str = "", *, env_examples: str) -> str:
    return textwrap.dedent(
        f"""\
        # {title}

        Supplementary reference: **exact aggregation pipeline** (as JSON) run by the **`{job}`** benchmark job on collection **`{coll}`**.

        {extra}

        ## Conventions

        - **`{SK}`** — replace with the `sellerKey` being benchmarked for that row.
        - **Atlas index name** and **text query** use this job’s Python defaults; override with environment variables documented on `mongo_bench.jobs.benchmarks.{job}` (e.g. {env_examples}).
        - **`run_timed_count`** (in `benchmark_fixtures.py`) appends `{{"$count": "c"}}` to the pipeline for timing and count; that stage is **not** shown below.

        ---

        """
    )


def filter_tests_md() -> str:
    lines = ["## `FILTER_TESTS` parameter dicts (from `benchmark_fixtures.py`)\n"]
    for name, params in FILTER_TESTS:
        lines.append(f"### `{name}`\n")
        lines.append("```json")
        lines.append(dumps(params))
        lines.append("```\n")
    return "\n".join(lines)


def main() -> None:
    si = _load("search_index")
    sw = _load("search_wildcard")
    sa = _load("search_atlas")

    compound_name = si._compound_search_name_stage(IDX_TEXT, SK, TQ)

    out_dir = Path(__file__).resolve().parent

    # --- search_index ---
    parts = [
        header(
            "`search_index` pipelines (`bench_index`)",
            "bench_index",
            "search_index",
            "MongoDB compound index: `bench_compound`. Atlas Search index: `bench_text`. `$match` uses sentinel `$ne: \"XXXXXX\"` on unused facet fields when any facet is set.",
            env_examples="`BENCH_INDEX_COLLECTION`, `BENCH_ATLAS_SEARCH_INDEX`, `BENCH_ATLAS_TEXT_QUERY`",
        ),
        filter_tests_md(),
        "## Pipelines per CSV label\n",
        "### `atlas_compound_sellerKey_name`\n",
        "Single-stage Atlas text + `sellerKey` (no facet `$match`).\n",
        "```json",
        dumps([compound_name]),
        "```\n",
    ]
    for test_name, params in FILTER_TESTS:
        flt = si.match_from_filter_test(SK, params)
        parts.append(f"### `match_{test_name}`\n")
        parts.append("```json")
        parts.append(dumps([{"$match": flt}]))
        parts.append("```\n")
        parts.append(f"### `atlas_plus_match_{test_name}`\n")
        parts.append("```json")
        parts.append(dumps([compound_name, {"$match": flt}]))
        parts.append("```\n")

    (out_dir / "search-index.md").write_text("\n".join(parts), encoding="utf-8")

    # --- search_wildcard ---
    parts = [
        header(
            "`search_wildcard` pipelines (`bench_wildcard`)",
            "bench_wildcard",
            "search_wildcard",
            "MongoDB wildcard index: `bench_wildcard_sellerKey_paths`. Atlas Search index: `bench_text`. `$match` includes **only** fields present in each `FILTER_TESTS` entry (no sentinels).",
            env_examples="`BENCH_WILDCARD_COLLECTION`, `BENCH_ATLAS_SEARCH_INDEX`, `BENCH_ATLAS_TEXT_QUERY`",
        ),
        filter_tests_md(),
        "## Pipelines per CSV label\n",
        "### `atlas_compound_sellerKey_name`\n",
        "Same `$search` shape as `search_index` (different collection).\n",
        "```json",
        dumps([compound_name]),
        "```\n",
    ]
    for test_name, params in FILTER_TESTS:
        flt = sw.match_from_filter_test(SK, params)
        parts.append(f"### `match_{test_name}`\n")
        parts.append("```json")
        parts.append(dumps([{"$match": flt}]))
        parts.append("```\n")
        parts.append(f"### `atlas_plus_match_{test_name}`\n")
        parts.append("```json")
        parts.append(dumps([compound_name, {"$match": flt}]))
        parts.append("```\n")

    (out_dir / "search-wildcard.md").write_text("\n".join(parts), encoding="utf-8")

    # --- search_atlas ---
    parts = [
        header(
            "`search_atlas` pipelines (`bench_search`)",
            "bench_search",
            "search_atlas",
            "Atlas Search only (no MongoDB `$match`). Index: `bench_search_index`. Facet filters are built by `_atlas_filter_clauses_from_filter_test_params` (string lists → `in`; `quantity_min` → `range` on `inventory.quantity`).",
            env_examples="`BENCH_SEARCH_COLLECTION`, `BENCH_SEARCH_ATLAS_INDEX`, `BENCH_ATLAS_TEXT_QUERY`",
        ),
        filter_tests_md(),
        "## Pipelines per CSV label\n",
    ]
    for test_name, params in FILTER_TESTS:
        only = sa._compound_search_atlas_stage(
            IDX_SEARCH, SK, TQ, include_text=False, filter_test_params=params
        )
        plus = sa._compound_search_atlas_stage(
            IDX_SEARCH, SK, TQ, include_text=True, filter_test_params=params
        )
        parts.append(f"### `atlas_only_{test_name}`\n")
        parts.append("Facet filters in `compound.filter` only (no `must` text on `product.name`).\n")
        parts.append("```json")
        parts.append(dumps([only]))
        parts.append("```\n")
        parts.append(f"### `atlas_plus_text_{test_name}`\n")
        parts.append(
            "Same filters plus `compound.must` with `text` on `product.name` when `BENCH_ATLAS_TEXT_QUERY` is non-blank after strip.\n"
        )
        parts.append("```json")
        parts.append(dumps([plus]))
        parts.append("```\n")

    (out_dir / "search-atlas.md").write_text("\n".join(parts), encoding="utf-8")

    readme = textwrap.dedent(
        f"""\
        # Benchmark aggregation pipelines (JSON)

        These files list every **test case** from `FILTER_TESTS` and the **aggregation pipeline** passed to `aggregate()` (before the internal `$count` stage), as JSON.

        | File | Job | Collection |
        |------|-----|------------|
        | [search-index.md](search-index.md) | `search_index` | `bench_index` |
        | [search-wildcard.md](search-wildcard.md) | `search_wildcard` | `bench_wildcard` |
        | [search-atlas.md](search-atlas.md) | `search_atlas` | `bench_search` |

        **Regenerate** after changing `FILTER_TESTS` or pipeline builders::

            cd /path/to/this-repository
            PYTHONPATH=src python3 docs/bench-pipelines/generate_pipeline_docs.py

        Canonical index and field definitions: `src/mongo_bench/resources/bench_collections.json`. Run summary: [benchmark-run-summary-2026-05-29.md](../benchmark-run-summary-2026-05-29.md).
        """
    )
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    print(f"Wrote {out_dir / 'README.md'}, search-index.md, search-wildcard.md, search-atlas.md")


if __name__ == "__main__":
    main()
