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
        - **Atlas index name** — set via environment variables documented on `mongo_bench.jobs.benchmarks.{job}` (e.g. {env_examples}).
        - **Name search query** — when a pipeline includes Atlas ``text`` on ``product.name``, the string comes from the ``text`` key in each merged benchmark case (`TEST_CASES` × `FILTER_TESTS` in ``benchmark_fixtures.py``), not from an environment variable.
        - **`BenchmarkSession.timed`** (in `benchmark_session.py`) appends `{{"$count": "c"}}` to the pipeline for timing and count; that stage is **not** shown below.

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
    sat = _load("search_attributes")
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
            env_examples="`BENCH_INDEX_COLLECTION`, `BENCH_ATLAS_SEARCH_INDEX`",
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
            env_examples="`BENCH_WILDCARD_COLLECTION`, `BENCH_ATLAS_SEARCH_INDEX`",
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

    # --- search_attributes ---
    parts = [
        header(
            "`search_attributes` pipelines (`bench_attributes`)",
            "bench_attributes",
            "search_attributes",
            "MongoDB compound index: `bench_attributes_compound` (``sellerKey``, ``attributes.key``, ``attributes.value``, ``inventory.quantity``). Atlas Search index: `bench_text`. ``$match`` uses ``$elemMatch`` on ``attributes`` for each facet dimension present in `FILTER_TESTS` (same keys as `merge_all._add_attributes`).",
            env_examples="`BENCH_ATTRIBUTES_COLLECTION`, `BENCH_ATLAS_SEARCH_INDEX`",
        ),
        filter_tests_md(),
        "## Pipelines per CSV label\n",
        "### `atlas_compound_sellerKey_name`\n",
        "Same `$search` shape as `search_index` (different collection / index definitions in `bench_collections.json`).\n",
        "```json",
        dumps([compound_name]),
        "```\n",
    ]
    for test_name, params in FILTER_TESTS:
        flt = sat.match_from_filter_test(SK, params)
        parts.append(f"### `match_{test_name}`\n")
        parts.append("```json")
        parts.append(dumps([{"$match": flt}]))
        parts.append("```\n")
        parts.append(f"### `atlas_plus_match_{test_name}`\n")
        parts.append("```json")
        parts.append(dumps([compound_name, {"$match": flt}]))
        parts.append("```\n")

    (out_dir / "search-attributes.md").write_text("\n".join(parts), encoding="utf-8")

    # --- search_atlas ---
    parts = [
        header(
            "`search_atlas` pipelines (`bench_search`)",
            "bench_search",
            "search_atlas",
            "Atlas Search only (no MongoDB `$match`). Index: `bench_search_index`. Facet filters are built by `_atlas_filter_clauses_from_filter_test_params` (string lists → `in`; `quantity_min` → `range` on `inventory.quantity`).",
            env_examples="`BENCH_SEARCH_COLLECTION`, `BENCH_SEARCH_ATLAS_INDEX`",
        ),
        filter_tests_md(),
        "## Pipelines per `FILTER_TESTS` row (representative `TEST_CASES` shapes)\n",
        "Each benchmark row uses :meth:`mongo_bench.jobs.benchmarks.benchmark_session.BenchmarkSession.iter_test_cases`; below, **no-text** omits `text` (facet-only `$search`), **with-text** sets `text` to the sample query.\n",
    ]
    for test_name, filt in FILTER_TESTS:
        pipe_no_text = sa._create_pipeline(IDX_SEARCH, SK, filters=filt)
        pipe_with_text = sa._create_pipeline(IDX_SEARCH, SK, filters=filt, text=TQ)
        parts.append(f"### `{test_name}` — no `text` in case dict\n")
        parts.append("```json")
        parts.append(dumps(pipe_no_text))
        parts.append("```\n")
        parts.append(f"### `{test_name}` — with `text` = `{TQ}`\n")
        parts.append("```json")
        parts.append(dumps(pipe_with_text))
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
        | [search-attributes.md](search-attributes.md) | `search_attributes` | `bench_attributes` |
        | [search-atlas.md](search-atlas.md) | `search_atlas` | `bench_search` |

        **Regenerate** after changing `FILTER_TESTS` or pipeline builders::

            cd /path/to/this-repository
            PYTHONPATH=src python3 docs/bench-pipelines/generate_pipeline_docs.py

        Canonical index and field definitions: `src/mongo_bench/resources/bench_collections.json`. Run summary: [benchmark-run-summary-2026-05-29.md](../benchmark-run-summary-2026-05-29.md).
        """
    )
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    print(f"Wrote {out_dir / 'README.md'}, search-index.md, search-wildcard.md, search-attributes.md, search-atlas.md")


if __name__ == "__main__":
    main()
