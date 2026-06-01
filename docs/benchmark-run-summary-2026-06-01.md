# Mongo benchmark run summary (2026-06-01)

This note documents the benchmark **collections and indexes** (`bench_collections.json`), the **shared document shape** (`merge_all`, including the **`attributes`** array on all `bench_*` collections), how each job **uses** those indexes, and **results from one CSV run per job** on **2026-06-01** after fixing seller tuple unpacking in `BenchmarkSession.iter_test_cases` (so `sellerKey` and `tier` align with `STATIC_BENCH_SELLER_KEYS` / `seller_keys_by_volume`). Approximate quantities use **≈** (Unicode U+2248) instead of ASCII `~`, because some Markdown renderers treat `~` as strikethrough delimiters.

## CSV inputs (single run each)

| Benchmark job | CSV file |
|----------------|----------|
| `search_index` | [`docs/runs/20260601/search_index_benchmark_20260601_152610.csv`](runs/20260601/search_index_benchmark_20260601_152610.csv) |
| `search_wildcard` | [`docs/runs/20260601/search_wildcard_benchmark_20260601_152755.csv`](runs/20260601/search_wildcard_benchmark_20260601_152755.csv) |
| `search_attributes` | [`docs/runs/20260601/search_attributes_benchmark_20260601_152718.csv`](runs/20260601/search_attributes_benchmark_20260601_152718.csv) |
| `search_atlas` | [`docs/runs/20260601/search_atlas_benchmark_20260601_152639.csv`](runs/20260601/search_atlas_benchmark_20260601_152639.csv) |

All jobs used **`FILTER_TESTS`**, **`TEST_CASES`**, and **`STATIC_BENCH_SELLER_KEYS`** from `benchmark_fixtures.py` at the time of the run (nine sellers: three small, three large, three medium). The matrix is **six** `TEST_CASES` families × **eight** `FILTER_TESTS` rows = **48** timed pipelines per seller (**432** CSV rows per job). Besides **`filters_only`** and **`search`**, the case families exercise **`$sort`**, **`$skip`**, and **`$limit`** (see **§3.3**). Name search uses **`Dragon`** wherever a case supplies a `text` field.

**Pipeline JSON (per test case):** [docs/bench-pipelines/README.md](bench-pipelines/README.md) — regenerate with `PYTHONPATH=src python3 docs/bench-pipelines/generate_pipeline_docs.py`.

---

## 1. Document shape and collection setup

### 1.1 Document shape

All `bench_*` collections share the shaped inventory document from `merge_all` (nested **`product`**, **`inventory`**, **`sellerKey`**, …). Each document also includes an **`attributes`** array of `{ "key", "value" }` pairs (same facet values as nested `product.*`) for **`bench_attributes`** and attribute-style benchmarks.

### 1.2 Four benchmark collections (authoritative: `bench_collections.json`)

| Collection | Purpose |
|------------|---------|
| **`bench_index`** | **Compound** MongoDB index (`bench_compound`) for structured filters; Atlas **`bench_text`** for `product.name` text + `sellerKey` in hybrid pipelines. |
| **`bench_wildcard`** | **Wildcard** MongoDB index (`bench_wildcard_sellerKey_paths`) with sparse `$match`; same Atlas **`bench_text`** as `bench_index` for mirrored hybrid runs. |
| **`bench_attributes`** | Same logical document as `bench_index`, with **attribute-pattern** filters backed by **`bench_attributes_compound`** (`sellerKey`, `attributes.key`, `attributes.value`, `inventory.quantity`); Atlas **`bench_text`** for the same text shape as `bench_index`. |
| **`bench_search`** | **Atlas-only** workloads on **`bench_search_index`** (no Mongo facet index in the spec). |

Re-run **`mongo-bench init`** (or apply `bench_schema`) after editing `bench_collections.json`.

### 1.2.1 `bench_attributes` compound index (new in this summary cycle)

The attribute-pattern collection uses a multikey-friendly compound index so `$elemMatch` on `attributes` can align with `sellerKey` and quantity:

```json
{
  "keys": [
    ["sellerKey", 1],
    ["attributes.key", 1],
    ["attributes.value", 1],
    ["inventory.quantity", 1],
    ["_id", 1]
  ],
  "options": {
    "name": "bench_attributes_compound"
  }
}
```

`search_attributes` builds **sparse** `$match` predicates: one `$elemMatch` per facet dimension present in each `FILTER_TESTS` row (see `search_attributes.py` and [search-attributes.md](bench-pipelines/search-attributes.md)).

### 1.3 Count correctness (Mongo hybrid jobs)

For **`filters_only_*`** rows (Mongo `$match` only, no leading `$search`), **median result counts across the three large static sellers** match **bit-for-bit** between **`search_index`**, **`search_wildcard`**, and **`search_attributes`** for every `FILTER_TESTS` name (e.g. `filters_only_no_filters` → **43,240**; `filters_only_multiple_filters_mtg` → **12**; …). That confirms the attribute `$elemMatch` encoding is semantically aligned with nested `product.*` filters on the same corpus.

**`search_atlas`** uses the same facet semantics in Atlas `compound.filter`; counts for the same scenarios agree with the Mongo jobs on this run.

---

## 2. Shared filter scenarios (`FILTER_TESTS`)

| `test_name` | Params (summary) |
|-------------|------------------|
| `no_filters` | `{}` — partition by `sellerKey` only |
| `multiple_filters_mtg` | MTG line + two sets + English + Normal |
| `multiple_filters_pkm` | Pokémon line + two sets + English + Holofoil |
| `line_and_rarity` | MTG line + rarity in {Common, Rare} |
| `line_and_languages` | MTG + {English, Japanese} + Normal |
| `product_line_only` | MTG line only |
| `product_line_with_quantity` | MTG line + `quantity_min: 10` |
| `rare_product_line` | Warhammer Age of Sigmar Champions TCG line |

**`search_index`** uses sentinel `$ne` on unused dimensions when any facet is set. **`search_wildcard`** and **`search_attributes`** use **sparse** predicates (only set dimensions). **`search_atlas`** maps the same params to Atlas `in` / `range` clauses.

---

## 3. Latency snapshot (large tier)

Unless noted, numbers are **median `elapsed_ms` across the three static large sellers** (`2413638f`, `1a5d3927`, `3da9b755`) from the CSVs above. Rows with errors are excluded (none on this run).

### 3.1 Facet-only stage: `filters_only_*` (no name query)

**Mongo jobs** (`search_index`, `search_wildcard`, `search_attributes`): `TEST_CASES` row **`filters_only`** supplies no `text`, so pipelines are **`$match`** only (compound / wildcard / `$elemMatch` on **`attributes`**).

**`search_atlas`**: same matrix row → a **single Atlas `$search`** on **`bench_search_index`** with **`compound.filter`** only (`equals` on **`sellerKey`** plus facet **`in`** / **`range`** from `FILTER_TESTS`). There is **no** `compound.must` **text** clause — this is the apples-to-apples **facet-only / no keyword** comparison to the Mongo `$match` rows above.

| `FILTER_TESTS` suffix | `search_index` (`bench_compound`) | `search_wildcard` | `search_attributes` (`bench_attributes_compound`) | **`search_atlas`** (`bench_search_index`, facet-only) |
|----------------------|------------------------------------:|------------------:|-----------------------------------------------------:|--------------------------------------------------------:|
| `no_filters` | **≈ 71 ms** | **≈ 1,200 ms** | **≈ 1,246 ms** | **≈ 1,702 ms** |
| `multiple_filters_mtg` | **≈ 54 ms** | **≈ 484 ms** | **≈ 428 ms** | **≈ 63 ms** |
| `multiple_filters_pkm` | **≈ 50 ms** | **≈ 436 ms** | **≈ 92 ms** | **≈ 62 ms** |
| `line_and_rarity` | **≈ 105 ms** | **≈ 329 ms** | **≈ 141 ms** | **≈ 526 ms** |
| `line_and_languages` | **≈ 107 ms** | **≈ 428 ms** | **≈ 159 ms** | **≈ 186 ms** |
| `product_line_only` | **≈ 100 ms** | **≈ 63 ms** | **≈ 126 ms** | **≈ 879 ms** |
| `product_line_with_quantity` | **≈ 118 ms** | **≈ 371 ms** | **≈ 105 ms** | **≈ 676 ms** |
| `rare_product_line` | **≈ 51 ms** | **≈ 50 ms** | **≈ 51 ms** | **≈ 57 ms** |

**Reading this table**

- **`filters_only_no_filters`** (seller partition only): **compound** (`bench_index`) stays **≈ tens–low hundreds of ms** on large sellers; **wildcard** and **attribute compound** both pay a heavy **full-partition style** scan (**≈ 1.2 s** median here). **`search_atlas`** with **only** `equals` on **`sellerKey`** is even slower (**≈ 1.7 s** median) — materializing the whole seller in Search with no narrowing facets.
- **Selective multi-field AND** (`multiple_filters_mtg`, `rare_product_line`, …): **compound** remains in a **≈ 50–118 ms** band. **`search_atlas`** often **matches or beats** compound here (**≈ 57–63 ms** medians) by resolving tight **`in`** filters entirely in **`bench_search_index`**. **Wildcard** / **attributes** remain more variable; **attributes** can still **beat wildcard** on some rows (e.g. **`multiple_filters_pkm`**).
- **Broad facets** (`product_line_only`, `line_and_rarity`, `product_line_with_quantity`): **`search_atlas`** can be **expensive** (**≈ hundreds of ms to ≈ 0.9 s** medians here) when many documents match the facet slice in Search alone — **compound** or **wildcard** may still win for these shapes on this corpus (**≈ 63–118 ms** compound; **≈ 63 ms** wildcard on **`product_line_only`**).
- **Broad line-only** (`product_line_only`): **wildcard** is **fastest** among Mongo jobs (**≈ 63 ms**); compound **≈ 100 ms**; attributes **≈ 126 ms**; Atlas facet-only **≈ 879 ms** on this run — **not** a default win for “line only” without a text or stronger constraint.

### 3.2 Text + facets: `search_*` (`$search` on `bench_text` / `bench_search_index`, then Mongo stages where applicable)

| `FILTER_TESTS` suffix | `search_index` | `search_wildcard` | `search_attributes` | `search_atlas` |
|---------------------|---------------:|------------------:|----------------------:|---------------:|
| `no_filters` | **≈ 88 ms** | **≈ 255 ms** | **≈ 484 ms** | **≈ 88 ms** |
| `multiple_filters_mtg` | **≈ 85 ms** | **≈ 86 ms** | **≈ 88 ms** | **≈ 52 ms** |
| `multiple_filters_pkm` | **≈ 88 ms** | **≈ 87 ms** | **≈ 89 ms** | **≈ 53 ms** |
| `line_and_rarity` | **≈ 86 ms** | **≈ 88 ms** | **≈ 89 ms** | **≈ 56 ms** |
| `line_and_languages` | **≈ 88 ms** | **≈ 85 ms** | **≈ 89 ms** | **≈ 55 ms** |
| `product_line_only` | **≈ 87 ms** | **≈ 89 ms** | **≈ 90 ms** | **≈ 58 ms** |
| `product_line_with_quantity` | **≈ 89 ms** | **≈ 85 ms** | **≈ 88 ms** | **≈ 58 ms** |
| `rare_product_line` | **≈ 85 ms** | **≈ 86 ms** | **≈ 92 ms** | **≈ 52 ms** |

**Observations**

- With **Atlas text** (`Dragon`) narrowing the candidate set first, **`search_index`** and **`search_wildcard`** medians **collapse to a tight band (≈ 85–90 ms)** — same **`bench_text`** stage, then a small `$match` / sort / skip/limit tail.
- **`search_attributes`** is **similar** for most facet rows but shows a **much slower** **`search_no_filters`** (**≈ 484 ms** vs **≈ 88 ms** on `search_index` on this run): same Atlas prefix, but the following **`$match`** is only `{ sellerKey }` (no `$elemMatch` facets), which may interact differently with the **multikey attribute** path than nested `product.*` on compound or wildcard. Worth profiling if `search_no_filters` on **`bench_attributes`** is a hot path.
- **`search_atlas`** **`search_*`** rows are often **faster than hybrid Mongo jobs** when facets are present (**≈ 52–58 ms** medians here): single **`$search`** resolves text + facets in Atlas (`bench_search_index`).

### 3.3 Sort, skip, limit, and what **`$count`** measures

The extra case families in **`TEST_CASES`** (`benchmark_fixtures.py`) append stages after the same **`$search`** / **`$match`** core as **`search`** or **`filters_only`**:

| Case name | Adds (after match / search) |
|-----------|-----------------------------|
| **`filters_and_deep_pagination`** | **`$sort`** on **`product.name`**, **`$skip` 1000**, **`$limit` 100** |
| **`search_and_sort_quantity`** | **`$sort`** on **`inventory.quantity`** |
| **`search_and_pagination`** | **`$sort`** on **`product.name`**, **`$skip` 10**, **`$limit` 10** |
| **`search_and_deep_pagination`** | **`$sort`** on **`product.name`**, **`$skip` 1000**, **`$limit` 100** |

**`BenchmarkSession.timed`** appends **`$count`** to the **full** pipeline, so the CSV **`count`** is the number of documents **emerging from the last stage** (after skip/limit). A **`$limit` 10** row therefore shows **`count = 10`** when at least ten documents survive; **`$skip` 1000** with fewer than 1000 matches yields **`count = 0`** even if latency stays in the same ballpark as the baseline **`search_*`** row.

**Effects in this run (large-tier medians from the CSVs)**

1. **Mongo-only deep page (`filters_and_deep_pagination_*` vs `filters_only_*`)**  
   - **`search_index`**: For **`no_filters`**, latency moves **≈ 71 ms → ≈ 87 ms** while **`count`** drops **43,240 → 100** (the page window). For **`product_line_only`**, **≈ 100 ms → ≈ 118 ms**, **`count` 21,891 → 100**.  
   - **`search_wildcard` / `search_attributes`**: On **`no_filters`**, adding sort/skip/limit **reduces** median latency (wildcard **≈ 1.2 s → ≈ 0.38 s**; attributes **≈ 1.25 s → ≈ 0.29 s**) while still returning **100** documents — the server does less work once the pipeline is bounded by the **limit** after the expensive partition scan.  
   - **`search_atlas`**: **`filters_and_deep_pagination_no_filters`** falls **≈ 1.7 s → ≈ 0.14 s** median with **`count` 100** — Atlas **`$search`** supports in-query **`sort` / `skip` / `limit`**, so deep paging can avoid materializing the whole seller facet-only result in one shot.

2. **Sort by quantity after text (`search_and_sort_quantity_*` vs `search_*`)**  
   On **`search_index`**, median ms and **`count`** stay **aligned** with **`search_*`** for the same filter (e.g. **`no_filters`**: **≈ 88 ms**, **789** hits) — an extra **`$sort`** on **`inventory.quantity`** on an already-small set is cheap here.

3. **Shallow pagination (`search_and_pagination_*`)**  
   **`count`** becomes **10** whenever enough documents pass the text + facet filter; median latency stays **within a few ms** of **`search_*`** on **`search_index`** / **`search_atlas`** (e.g. **`product_line_only`**: **≈ 87 ms** vs **≈ 87–89 ms** baseline, **`count` 10** vs **163**).

4. **Deep pagination on text (`search_and_deep_pagination_*`)**  
   For **`product_line_only`**, **`Dragon`** yields a **median `count` of 163** on large sellers for **`search_*`** — **below** **`skip` 1000**, so **`search_and_deep_pagination_product_line_only`** returns **`count = 0`** for **all four jobs** while latency remains **≈ 88–90 ms** (hybrid) or **≈ 63 ms** (Atlas): you still pay for **`$search`** + match + sort, but the page is **empty**. For **`no_filters`**, **`search_*`** has **789** hits **\< 1000**, so **`search_and_deep_pagination_no_filters`** also reports **`count = 0`** on this corpus.

5. **`search_attributes` + `search_no_filters`**  
   Baseline **`search_no_filters`** is slow (**≈ 484 ms** median, §3.2). Adding **`$skip`/`$limit`** in **`search_and_pagination_*`** / **`search_and_deep_pagination_*`** drops median latency to **≈ 85–86 ms** with **`count` 10** or **0** — most time was tied to materializing a large intermediate set; **pagination stages bound** what **`$count`** observes.

### 3.4 `search_atlas` facet-only (cross-reference)

Facet-only Atlas timings for every **`filters_only_*`** row are in **§3.1** (same CSV run, **no** `text` / `must` clause). Hybrid **`search_*`** rows with **`Dragon`** remain in **§3.2**; sort/skip/limit behavior for Atlas is covered in **§3.3**.

### 3.5 Small seller sanity check

For seller **`3617b942`** (small tier), **`filters_only_no_filters`** returns **count = 1** with **≈ 49–61 ms** across all four jobs — consistent with a tiny partition and correct **`sellerKey`** wiring after the tuple-order fix.

---

## 4. Cross-cutting observations

1. **Counts**: **`filters_only_*`** medians match across **`bench_index`**, **`bench_wildcard`**, and **`bench_attributes`** on large sellers; **`search_atlas`** matches the same semantics.
2. **Structured facets at large cardinality (§3.1)**: **`bench_compound`** keeps many **`filters_only_*`** workloads in a **≈ 50–120 ms** median band; **wildcard** and **attribute** indexes trade off depending on predicate shape. **`search_atlas`** facet-only is **fastest** on tight **`multiple_filters_*`** / **`rare_product_line`** here, but **slowest** on **`no_filters`**, **`product_line_only`**, and several **broad** facet slices — compare the full five-way table in **§3.1**.
3. **Text + facets**: Hybrid **`bench_text`** + Mongo tail is **≈ 85–90 ms** median for most **`search_*`** rows on **`bench_index`** / **`bench_wildcard`** / **`bench_attributes`** (except the **`search_no_filters`** outlier on **`bench_attributes`** — see §3.2).
4. **Sort / skip / limit (§3.3)**: **`$count`** reflects documents **after** pagination; **`search_and_deep_pagination_*`** can show **`count = 0`** when **`skip`** exceeds the **`Dragon`** hit count. **`search_atlas`** can fold sort/skip/limit into **`$search`**, changing facet-only deep-page cost vs Mongo follow-on stages.
5. **Operational**: **`iter_test_cases`** must iterate **`(seller_key, tier)`** tuples from **`STATIC_BENCH_SELLER_KEYS`** / **`seller_keys_by_volume`**; swapping them silently queried **`sellerKey: "small"`** etc. before the 2026-06-01 fix.

---

## 5. Short conclusion

| Approach | Strength in this run | Risk |
|----------|---------------------|------|
| **Compound + `$match` (`bench_index`)** | Best overall **`filters_only_*`** medians on large sellers; predictable **`search_*`** hybrid latency | Second stage after Atlas when using hybrid pattern |
| **Wildcard (`bench_wildcard`)** | Flexible paths; **`product_line_only`** can win | Very expensive **seller-only** and some tight AND facets vs compound |
| **Attribute pattern (`bench_attributes`)** | Count parity with nested `product` filters; competitive on some selective rows (e.g. PKM multi-filter) | **Seller-only** and **`search_no_filters`** can be **much slower** than compound in this snapshot |
| **Atlas-only (`bench_search`)** | **Facet-only (§3.1):** often **fastest** on tight **`multiple_filters_*`** / **`rare_product_line`**; **`search_*` (§3.2):** often **fastest** when text + facets | **Facet-only:** **`no_filters`** and **broad** slices (**`product_line_only`**, **`line_and_rarity`**, …) can be **≈ 0.5–1.7 s** on large sellers here |

**Practical default** remains: **`sellerKey`-first compound** for heavy structured inventory filters; add **`bench_attributes`** (or attribute-style schemas) when documents are stored as key/value arrays and you want index-aligned `$elemMatch` — but **validate** seller-only and text-only tails on real cardinality. Use **Atlas-only** when a single **`$search`** should own both text and facets and mappings cover all dimensions.

---

*Numbers cited from the CSV files under [`docs/runs/20260601/`](runs/20260601/); medians use the three static **large** sellers unless noted. Earlier write-up for a two-run matrix and older `FILTER_TESTS` names: [benchmark-run-summary-2026-05-29.md](benchmark-run-summary-2026-05-29.md).*
