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

Canonical index and field definitions: `src/mongo_bench/resources/bench_collections.json`. Run summaries: [benchmark-run-summary-2026-06-01.md](../benchmark-run-summary-2026-06-01.md) (latest, includes `bench_attributes`); [benchmark-run-summary-2026-05-29.md](../benchmark-run-summary-2026-05-29.md).
