# Mongo benchmark run summary (2026-05-29)

This note documents the benchmark **collections and indexes** (`bench_collections.json`), the **shared document shape** (`merge_all`), how each job **uses** those indexes, and **results from two back-to-back CSV runs** per job (counts identical across runs; timings averaged where cited). Approximate quantities use **≈** (Unicode U+2248) instead of ASCII `~`, because some Markdown renderers treat `~` as strikethrough delimiters.

## CSV inputs (two runs each)

| Benchmark job | Run 1 | Run 2 |
|----------------|-------|-------|
| `search_index` | `search_index_benchmark_20260529_182813.csv` | `search_index_benchmark_20260529_182827.csv` |
| `search_wildcard` | `search_wildcard_benchmark_20260529_182845.csv` | `search_wildcard_benchmark_20260529_182907.csv` |
| `search_atlas` | `search_atlas_benchmark_20260529_182716.csv` | `search_atlas_benchmark_20260529_182747.csv` |

All jobs used **`FILTER_TESTS`** and **`STATIC_BENCH_SELLER_KEYS`** from `benchmark_fixtures.py` (nine sellers: three small, three large, three medium). Name search used the **`Dragon`** string from **`TEST_CASES`** rows that include a `text` field (not an environment variable).

**Pipeline JSON (per test case):** [docs/bench-pipelines/README.md](bench-pipelines/README.md) — generated reference for each job’s aggregation stages; regenerate with `PYTHONPATH=src python3 docs/bench-pipelines/generate_pipeline_docs.py`.

---

## 1. Document shape and collection setup

### 1.1 Document shape

All collections use the following document shape for testing:

```json
{
  "_id": "0009b887:X0BLjZ9aw6dwLHpV0z5q7VAmn",
  "pamKey": "X0BLjZ9aw6dwLHpV0z5q7VAmn",
  "sellerKey": "0009b887",
  "inventory": {
    "quantity": 16,
    "reserveQuantity": 1,
    "lastUpdated": "2026-03-13T14:49:21.964830+00:00"
  },
  "product": {
    "id": "gsWbww83fwQpjaMFBZRv6Vw",
    "name": "Icefall",
    "productLine": "Magic The Gathering TCG",
    "set": "Coldsnap",
    "cardNumber": "85",
    "language": "Japanese",
    "printing": "Normal",
    "rarity": "Common",
    "type": "Card Single"
  }
}
```

The `merge_all` job (when run against sandbox) can populate each of the collections with data pulled from raw feeds. When running in a local mongo container the collections would need to be generated.

### 1.2 Three benchmark collections (authoritative: `bench_collections.json`)

There are 3 collections created for different scenarios:

|collection|purpose|
|---|---|
|`bench_index`|test use of **compound index** for filters, additional **atlas index** for text-only fields (`product.name`) to allow free-text search. Search pipeline is either `$match` only or `$search`->`$match`|
|`bench_wildcard`|test use of **wildcard index** for filters, additional **atlas index** for text-only fields (`product.name`) to allow free-text search. Search pipeline is either `$match` only or `$search`->`$match`|
|`bench_search`|test use of **atlas search index only** - all search paths go through `$search` aggregation|

Specifications for the collections can be found and edited in `bench_collections.json`.

Re-run **`mongo-bench init`** (or apply `bench_schema`) after editing `bench_collections.json` so Mongo and Atlas definitions stay aligned.

### 1.2.1 `bench_index` collection

This collection is the bases for testing a **compound index** approach using sentinel values to ensure index usage. Here is an [article](https://medium.com/mongodb/searching-mongodb-by-arbitrary-combinations-of-fields-0c9e64bd1e00) explaining this approach.

The collection is created with this index specification:

```json
{
  "keys": [
    ["sellerKey", 1],
    ["product.productLine", 1],
    ["product.set", 1],
    ["product.language", 1],
    ["product.printing", 1],
    ["product.rarity", 1],
    ["product.type", 1],
    ["inventory.quantity", 1]
  ],
  "options": {
    "name": "bench_compound"
  }
}
```

### 1.2.2 `bench_wildcard` collection

This collection is used to test the [wildcard index](https://www.mongodb.com/docs/manual/core/indexes/index-types/index-wildcard/index-wildcard-compound/#filter-fields-with-a-wildcardprojection). 

This collection is created with this index specification:

```json
{
  "keys": [
    ["sellerKey", 1],
    ["$**", 1]
  ],
  "options": {
    "name": "bench_wildcard_sellerKey_paths",
    "wildcardProjection": {
      "product.productLine": 1,
      "product.set": 1,
      "product.language": 1,
      "product.printing": 1,
      "product.rarity": 1,
      "product.type": 1,
      "inventory.quantity": 1
    }
  }
}
```

### 1.2.3 `bench_search` collection

This collection is made to test using **only** atlas search for all scenarios. 

The atlas index specification can be found in `bench_collections.json`

### 1.3 Physical size and MongoDB indexes (MongoDB Compass)

On this corpus, all three benchmark collections hold the **same 209,000 documents** (**96.35 MB** logical data, **461 B** average document size). **Storage size** on disk for the collection data is **≈ 42.5–42.6 MB** per collection (similar across them). What differs is **how many MongoDB indexes** exist and **how large they are**:

| Collection | MongoDB indexes (count) | Total MongoDB index size |
|------------|------------------------|---------------------------|
| **`bench_search`** | **1** (typically `_id` only; no compound / wildcard bench index in the spec) | **≈ 12.6 MB** |
| **`bench_index`** | **2** (`_id` + **`bench_compound`**) | **≈ 24.9 MB** |
| **`bench_wildcard`** | **2** (`_id` + **`bench_wildcard_sellerKey_paths`**) | **≈ 53.8 MB** |

So **`bench_wildcard`** carries the **largest MongoDB index footprint** in this snapshot—**well over 2×** the compound index collection and **≈ 4×** the Mongo-side index total on **`bench_search`**. Atlas Search indexes are managed separately in Atlas and are not included in these Compass “index size” figures.

### 1.4 Text search + structured filters: how the three benchmarks differ

All three jobs use the same **`Dragon`** keyword on **`product.name`** wherever **`TEST_CASES`** includes a **`text`** field, combined with the same **`FILTER_TESTS`** facet params, but **where** text and facets run—and **what CSV labels** mean—differs. That is the main architectural split for “search UI: keyword + facets.”

| Benchmark | Collection | CSV label for “text + facets” | Pipeline shape | Role of Mongo vs Atlas |
|-----------|------------|------------------------------|----------------|-------------------------|
| **`search_index`** | **`bench_index`** | **`atlas_plus_match_{test}`** | **`$search`** on Atlas index **`bench_text`** (`equals` `sellerKey` + **`must`** `text` on `product.name`) **then** **`$match`** using **`bench_compound`** (sentinel `$ne` pattern) | **Hybrid / layered**: Atlas handles **tokenization / relevance** on the name field; Mongo applies **structured facets** on a **prefix compound** index. This matches a common production pattern: “narrow or rank in Search, enforce facets in the document DB.” |
| **`search_wildcard`** | **`bench_wildcard`** | **`atlas_plus_match_{test}`** (same label family as index) | Same **two-stage** order as **`search_index`**, but **`$match`** uses **sparse** predicates aligned to **`bench_wildcard_sellerKey_paths`** | Same **Atlas-then-Mongo** split as index; facet stage cost still follows **wildcard** vs **compound** behavior on **`match_*`** (see §4). |
| **`search_atlas`** | **`bench_search`** | **`atlas_plus_text_{test}`** | **Single** **`$search`** on **`bench_search_index`**: `compound.filter` = `sellerKey` + facet **`in`** / **`range`**; **`compound.must`** = **`text`** on `product.name` | **All-in-Atlas**: one request, one **`$search`**; facets use **explicit** mappings (e.g. **`lucene.keyword`** on line/set). No Mongo facet index on this collection. |

**Counts** for the intersection of **`Dragon`** + a given facet scenario **agree** across these modes (e.g. **`atlas_plus_match_*`** on **`bench_index`** matches **`atlas_plus_text_*`** on **`bench_search`** for the same `sellerKey` and test name).

**Latency (large tier, median across three static large sellers; each cell = mean of two CSV runs per seller)** — text + facets:

| `FILTER_TESTS` name | **`bench_index`** `atlas_plus_match_*` | **`bench_wildcard`** `atlas_plus_match_*` | **`bench_search`** `atlas_plus_text_*` |
|---------------------|----------------------------------------:|------------------------------------------:|----------------------------------------:|
| `seller_only` | **≈ 84 ms** | **≈ 86 ms** | **≈ 91 ms** |
| `multiple_filters_mtg` | **≈ 86 ms** | **≈ 86 ms** | **≈ 55 ms** |
| `multiple_filters_pkm` | **≈ 86 ms** | **≈ 86 ms** | **≈ 56 ms** |
| `sparse_filters` | **≈ 85 ms** | **≈ 87 ms** | **≈ 57 ms** |
| `multiple_languages` | **≈ 86 ms** | **≈ 86 ms** | **≈ 54 ms** |
| `product_line_only` | **≈ 87 ms** | **≈ 86 ms** | **≈ 64 ms** |
| `product_line_with_quantity` | **≈ 87 ms** | **≈ 88 ms** | **≈ 60 ms** |
| `rare_product_lines` | **≈ 85 ms** | **≈ 87 ms** | **≈ 54 ms** |

**How to read this for `bench_index`:** for **`seller_only`**, **`atlas_plus_match_seller_only`** is slightly **faster** than **`atlas_plus_text_seller_only`** on **`bench_search`** (≈ 84 ms vs ≈ 91 ms median here): Mongo’s **`$match`** after Atlas only touches the **text-hit** subset. Once **additional facets** are present, **`atlas_plus_text_*`** on **`bench_search`** is often **about 25–35% faster** in these medians than **`atlas_plus_match_*`** on **`bench_index`**, because facets and text are resolved in **one** Search query with **keyword-style** facet fields, whereas **`atlas_plus_match_*`** still pays for a **second** stage (`$match` over Atlas output) on the application database.

**Why you might still prefer `bench_index` + `atlas_plus_match_*`:** smaller **Mongo index** footprint than wildcard, predictable **compound** plans for **`$match`**, reuse of the same documents for **non-Search** workloads, and a clear split between **Search analyzers** (`bench_text`) and **exact facet** semantics in Mongo—even if this run shows a modest **extra** cost vs all-in-Atlas for facet-heavy text queries.

---

## 2. Shared filter scenarios (`FILTER_TESTS`)

Each scenario is a `(test_name, params)` pair. **`search_index`** builds full facet predicates with **`$ne` sentinels** on unused dimensions so the compound index stays aligned. **`search_wildcard`** omits unset dimensions so the wildcard index can serve sparse `$match`. **`search_atlas`** maps the same params to Atlas **`compound.filter`** (`equals` on `sellerKey`, `in` on string paths, `range` on `inventory.quantity` when `quantity_min` is set).

| `test_name` | Params (summary) |
|-------------|------------------|
| `seller_only` | `{}` — partition by `sellerKey` only |
| `multiple_filters_mtg` | MTG line + two sets + English + Normal |
| `multiple_filters_pkm` | Pokémon line + two sets + English + Holofoil |
| `sparse_filters` | MTG line + rarity in {Common, Rare} |
| `multiple_languages` | MTG + {English, Japanese} + Normal |
| `product_line_only` | MTG line only |
| `product_line_with_quantity` | MTG line + `quantity_min: 10` |
| `rare_product_lines` | `$in` on three low-volume product lines |

---

## 3. `search_index` (`bench_index`)

### 3.1 How the job uses indexes

- **MongoDB**: timed **`$match`** pipelines use **`bench_compound`** via `_create_filter`: leading `sellerKey`, then `$in` (or **`$ne: "XXXXXX"`** sentinel) on each projected facet so the planner can use the compound index shape consistently.
- **Atlas**: baseline **`atlas_compound_sellerKey_name`** — single `$search` on **`bench_text`**: `compound.filter` = `equals` on `sellerKey`; `compound.must` = **`text`** on **`product.name`** using the query string from the benchmark case (`TEST_CASES` / merged params).
- **Combined**: for each filter test, **`atlas_plus_match_{test}`** runs the same `$search` stage followed by **`$match`** with the same predicate as **`match_{test}`** (Atlas text + `sellerKey` first, then compound-backed facet match). See **§1.4** for how this differs from **`atlas_plus_text_*`** on **`bench_search`** and for median timings.

### 3.2 Correctness across backends

For every **`match_*`** scenario, **document counts match** between `search_index` and `search_wildcard`, and **`atlas_only_*`** counts on **`bench_search`** match **`match_*`** counts on **`bench_index`** (same `sellerKey` and scenario). **Across the two CSV runs**, counts are **bit-for-bit identical** for every row.

### 3.3 Results (high level)

- **Cold / warm**: first **`atlas_compound_sellerKey_name`** on the first small seller is still **≈ 528–530 ms** in both index runs (Atlas warm-up / plan behavior); subsequent similar Atlas calls on that tier drop to **≈ 50–56 ms**.
- **`text` + `Dragon`**: on **small** sellers, **`atlas_compound`** often returns **0** hits; on **large** sellers in this dataset it returns **hundreds** of hits (e.g. 563 / 789 / 901 for the three static large keys), so Atlas timings are no longer “empty-set only” at large scale.
- **`$match` latency (large tier, median across three large sellers; each point is the mean of two runs)**:
  - **`match_seller_only`**: **≈ 63 ms**
  - **`match_multiple_filters_mtg`**: **≈ 51 ms**
  - **`match_sparse_filters`**: **≈ 75 ms**
  - **`match_product_line_only`**: **≈ 73 ms**
- **`atlas_plus_match_*`** on large sellers is **≈ 84–88 ms** median across scenarios in this run (see **§1.4** table): the Atlas stage returns the **`Dragon`** hit set for the seller, then **`$match`** applies facets on **`bench_compound`**.

---

## 4. `search_wildcard` (`bench_wildcard`)

### 4.1 How the job uses indexes

- **MongoDB**: **`$match`** uses **`_create_wildcard_filter`** — only keys present in the scenario (no sentinels), so predicates stay within **`wildcardProjection`** paths under **`bench_wildcard_sellerKey_paths`**.
- **Atlas**: same **`bench_text`** baseline and **`atlas_plus_match_*`** pattern as **`search_index`** (mirrored pipeline shapes; see **§1.4** for text+facet vs **`bench_search`**).

### 4.2 Results (high level)

On **large** sellers, **selective multi-field `$in` AND** remains expensive relative to the compound index, while **broad** `product_line_only` can be **similar or faster** on wildcard than compound when both plans devolve to large scans.

**Median ms (large tier, three sellers, mean of two runs)** — compare to **`search_index`**:

| Scenario | `search_index` | `search_wildcard` | Wildcard / index |
|----------|----------------:|------------------:|------------------:|
| `match_seller_only` | ≈ 63 | ≈ 254 | **≈ 4.0×** |
| `match_multiple_filters_mtg` | ≈ 51 | ≈ 275 | **≈ 5.4×** |
| `match_sparse_filters` | ≈ 75 | ≈ 279 | **≈ 3.7×** |
| `match_product_line_only` | ≈ 73 | ≈ 63 | **≈ 0.9×** |
| `atlas_plus_match_seller_only` | ≈ 84 | ≈ 86 | **≈ 1.0×** |

For **`atlas_plus_match_*`**, **`bench_index`** and **`bench_wildcard`** medians are **within ≈ 1–3 ms** here because both use the same **`bench_text`** `$search` first; the **`$match`** step sees an already small candidate set. Contrast **`atlas_plus_text_*`** on **`bench_search`** (**§1.4**): one Search stage, often lower latency when facets are present.

---

## 5. `search_atlas` (`bench_search`)

### 5.1 How the job uses indexes

- **MongoDB**: none for this collection (per spec).
- **Atlas**: single **`$search`** on **`bench_search_index`**. For each `FILTER_TESTS` entry, two pipelines:
  - **`atlas_only_{test}`**: `compound.filter` only — `equals` on **`sellerKey`** plus **`in`** / **`range`** clauses derived from the same params as Mongo (`product.productLine`, `product.set`, `product.language`, `product.printing`, `product.rarity`, `product.type`, `inventory.quantity`).
  - **`atlas_plus_text_{test}`**: same filters, plus **`compound.must`** with **`text`** on **`product.name`** when the merged case supplies a non-blank query string (e.g. **`Dragon`** from **`TEST_CASES`**). This is the **single-stage** analogue of **`search_index`**’s **`atlas_plus_match_{test}`**; compare timings in **§1.4**.

Explicit **`lucene.keyword`** (with `token`) on **`productLine`** and **`set`** in **`bench_search_index`** keeps facet **`in`** filters aligned with stored string values — this run shows **non-zero** `atlas_only_*` counts wherever the corresponding **`match_*`** counts are non-zero.

### 5.2 Results (high level)

- **Facet-only vs text+facets**: **`atlas_only_seller_only`** on large sellers is **very expensive** (median **≈ 1.7 s** across the three large keys in these runs) because it effectively materializes the whole seller catalog in Search. Adding **`product_line`** or other filters drops cost (e.g. **`atlas_only_product_line_only`** median **≈ 873 ms**; **`atlas_only_sparse_filters`** median **≈ 521 ms**).
- **Text constraint**: **`atlas_plus_text_seller_only`** median **≈ 91 ms** on large sellers with **hundreds** of hits — intersecting **`Dragon`** with `sellerKey` is far cheaper than **`atlas_only_seller_only`** (≈ 1.7 s median). With **extra facets**, **`atlas_plus_text_*`** often **beats** **`atlas_plus_match_*`** on **`bench_index`** in these medians (**§1.4**), at the cost of encoding all facet semantics in **`bench_search_index`**.
- **First small seller**: **`atlas_only_seller_only`** shows **≈ 526 ms vs ≈ 818 ms** between the two runs (first-touch variance); steady-state small-seller rows are mostly **≈ 50–80 ms** for scoped scenarios.

---

## 6. Cross-cutting observations

1. **Counts**: **`match_*`** agrees between **`bench_index`** and **`bench_wildcard`**; **`atlas_only_*`** on **`bench_search`** agrees with **`match_*`** on **`bench_index`**. Two runs per job produced **no count drift**.
2. **Structured facets at large cardinality**: **`bench_compound` + `$match`** keeps selective AND filters in the **≈ 50–80 ms** (median) range on large sellers; **`bench_wildcard_sellerKey_paths`** can be **several× slower** on the same tight predicates.
3. **Atlas-only on full seller**: **`atlas_only_seller_only`** is a poor stand-in for “Mongo `sellerKey` partition scan” cost — prefer **`equals` + additional filters** or a **text / must** clause to bound work, as in **`atlas_plus_text_*`**.
4. **Operational**: the bundled matrix uses **`Dragon`** in **`TEST_CASES`** where a name search applies; behavior is **tier-dependent** on the name field (often **0** on small static sellers for pure-text stages, non-zero on large). For product decisions, also benchmark a term sampled from real **`product.name`** data.
5. **Text + facets (§1.4)**: **`bench_index`** **`atlas_plus_match_*`** trades a **second** pipeline stage for **compound-index** facet enforcement and a smaller **Mongo** index than **`bench_wildcard`** (**§1.3**). **`bench_search`** **`atlas_plus_text_*`** is often **faster** when facets narrow inside one **`$search`**, but requires **full** facet coverage in the Atlas mapping.

---

## 7. Short conclusion

| Approach | Strength in this run | Risk |
|----------|---------------------|------|
| **Compound + `$match` (`bench_index`)** | Best **`match_*`** latency on selective facets; **`atlas_plus_match_*`** = text in Atlas + facets in Mongo (**§1.4**) | **`atlas_plus_match_*`** can trail **`atlas_plus_text_*`** when facets are heavy; index key order must match filters |
| **Wildcard + `$match` (`bench_wildcard`)** | Same counts as compound; flexible paths | Large slowdowns on tight AND filters for very large `sellerKey` slices |
| **Atlas-only (`bench_search` + `bench_search_index`)** | **`atlas_plus_text_*`** often **fastest** text+facet medians here; explicit mappings align counts with Mongo | **`atlas_only_*`** without strong filters can be **seconds** on the largest sellers; all facets must live in Search mappings |

**Practical default** for structured inventory search: **`sellerKey`-first compound Mongo indexes + `$match`** for facets, with **Atlas** used for text/relevance or post-filtering on a **bounded** set — or **`compound.must`** text up front when using Atlas-only, as in these benchmarks.

---

*Numbers cited from the six CSV files in the repository root; medians use the three static **large** sellers and the mean of the two runs per seller. Collection/index sizes from a MongoDB Compass snapshot of the same 209K-doc corpus (**§1.3**).*
