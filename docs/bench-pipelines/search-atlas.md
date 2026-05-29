# `search_atlas` pipelines (`bench_search`)

Supplementary reference: **exact aggregation pipeline** (as JSON) run by the **`search_atlas`** benchmark job on collection **`bench_search`**.

Atlas Search only (no MongoDB `$match`). Index: `bench_search_index`. Facet filters are built by `_atlas_filter_clauses_from_filter_test_params` (string lists → `in`; `quantity_min` → `range` on `inventory.quantity`).

## Conventions

- **`<SELLER_KEY>`** — replace with the `sellerKey` being benchmarked for that row.
- **Atlas index name** and **text query** use this job’s Python defaults; override with environment variables documented on `mongo_bench.jobs.benchmarks.search_atlas` (e.g. `BENCH_SEARCH_COLLECTION`, `BENCH_SEARCH_ATLAS_INDEX`, `BENCH_ATLAS_TEXT_QUERY`).
- **`run_timed_count`** (in `benchmark_fixtures.py`) appends `{"$count": "c"}` to the pipeline for timing and count; that stage is **not** shown below.

---


## `FILTER_TESTS` parameter dicts (from `benchmark_fixtures.py`)

### `seller_only`

```json
{}
```

### `multiple_filters_mtg`

```json
{
  "product_line": [
    "Magic The Gathering TCG"
  ],
  "product_sets": [
    "Commander Legends",
    "Aetherspiral"
  ],
  "language": [
    "English"
  ],
  "printing": [
    "Normal"
  ]
}
```

### `multiple_filters_pkm`

```json
{
  "product_line": [
    "Pokémon TCG"
  ],
  "product_sets": [
    "League & Championship Cards",
    "SWSH01: Sword & Shield Base Set"
  ],
  "language": [
    "English"
  ],
  "printing": [
    "Holofoil"
  ]
}
```

### `sparse_filters`

```json
{
  "product_line": [
    "Magic The Gathering TCG"
  ],
  "rarity": [
    "Common",
    "Rare"
  ]
}
```

### `multiple_languages`

```json
{
  "product_line": [
    "Magic The Gathering TCG"
  ],
  "language": [
    "English",
    "Japanese"
  ],
  "printing": [
    "Normal"
  ]
}
```

### `product_line_only`

```json
{
  "product_line": [
    "Magic The Gathering TCG"
  ]
}
```

### `product_line_with_quantity`

```json
{
  "product_line": [
    "Magic The Gathering TCG"
  ],
  "quantity_min": 10
}
```

### `rare_product_lines`

```json
{
  "product_line": [
    "Union Arena",
    "Argent Saga TCG",
    "Warhammer Age of Sigmar Champions TCG"
  ]
}
```

## Pipelines per CSV label

### `atlas_only_seller_only`

Facet filters in `compound.filter` only (no `must` text on `product.name`).

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_plus_text_seller_only`

Same filters plus `compound.must` with `text` on `product.name` when `BENCH_ATLAS_TEXT_QUERY` is non-blank after strip.

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          }
        ],
        "must": [
          {
            "text": {
              "path": "product.name",
              "query": "Dragon"
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_only_multiple_filters_mtg`

Facet filters in `compound.filter` only (no `must` text on `product.name`).

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Magic The Gathering TCG"
              ]
            }
          },
          {
            "in": {
              "path": "product.set",
              "value": [
                "Commander Legends",
                "Aetherspiral"
              ]
            }
          },
          {
            "in": {
              "path": "product.language",
              "value": [
                "English"
              ]
            }
          },
          {
            "in": {
              "path": "product.printing",
              "value": [
                "Normal"
              ]
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_plus_text_multiple_filters_mtg`

Same filters plus `compound.must` with `text` on `product.name` when `BENCH_ATLAS_TEXT_QUERY` is non-blank after strip.

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Magic The Gathering TCG"
              ]
            }
          },
          {
            "in": {
              "path": "product.set",
              "value": [
                "Commander Legends",
                "Aetherspiral"
              ]
            }
          },
          {
            "in": {
              "path": "product.language",
              "value": [
                "English"
              ]
            }
          },
          {
            "in": {
              "path": "product.printing",
              "value": [
                "Normal"
              ]
            }
          }
        ],
        "must": [
          {
            "text": {
              "path": "product.name",
              "query": "Dragon"
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_only_multiple_filters_pkm`

Facet filters in `compound.filter` only (no `must` text on `product.name`).

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Pokémon TCG"
              ]
            }
          },
          {
            "in": {
              "path": "product.set",
              "value": [
                "League & Championship Cards",
                "SWSH01: Sword & Shield Base Set"
              ]
            }
          },
          {
            "in": {
              "path": "product.language",
              "value": [
                "English"
              ]
            }
          },
          {
            "in": {
              "path": "product.printing",
              "value": [
                "Holofoil"
              ]
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_plus_text_multiple_filters_pkm`

Same filters plus `compound.must` with `text` on `product.name` when `BENCH_ATLAS_TEXT_QUERY` is non-blank after strip.

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Pokémon TCG"
              ]
            }
          },
          {
            "in": {
              "path": "product.set",
              "value": [
                "League & Championship Cards",
                "SWSH01: Sword & Shield Base Set"
              ]
            }
          },
          {
            "in": {
              "path": "product.language",
              "value": [
                "English"
              ]
            }
          },
          {
            "in": {
              "path": "product.printing",
              "value": [
                "Holofoil"
              ]
            }
          }
        ],
        "must": [
          {
            "text": {
              "path": "product.name",
              "query": "Dragon"
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_only_sparse_filters`

Facet filters in `compound.filter` only (no `must` text on `product.name`).

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Magic The Gathering TCG"
              ]
            }
          },
          {
            "in": {
              "path": "product.rarity",
              "value": [
                "Common",
                "Rare"
              ]
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_plus_text_sparse_filters`

Same filters plus `compound.must` with `text` on `product.name` when `BENCH_ATLAS_TEXT_QUERY` is non-blank after strip.

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Magic The Gathering TCG"
              ]
            }
          },
          {
            "in": {
              "path": "product.rarity",
              "value": [
                "Common",
                "Rare"
              ]
            }
          }
        ],
        "must": [
          {
            "text": {
              "path": "product.name",
              "query": "Dragon"
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_only_multiple_languages`

Facet filters in `compound.filter` only (no `must` text on `product.name`).

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Magic The Gathering TCG"
              ]
            }
          },
          {
            "in": {
              "path": "product.language",
              "value": [
                "English",
                "Japanese"
              ]
            }
          },
          {
            "in": {
              "path": "product.printing",
              "value": [
                "Normal"
              ]
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_plus_text_multiple_languages`

Same filters plus `compound.must` with `text` on `product.name` when `BENCH_ATLAS_TEXT_QUERY` is non-blank after strip.

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Magic The Gathering TCG"
              ]
            }
          },
          {
            "in": {
              "path": "product.language",
              "value": [
                "English",
                "Japanese"
              ]
            }
          },
          {
            "in": {
              "path": "product.printing",
              "value": [
                "Normal"
              ]
            }
          }
        ],
        "must": [
          {
            "text": {
              "path": "product.name",
              "query": "Dragon"
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_only_product_line_only`

Facet filters in `compound.filter` only (no `must` text on `product.name`).

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Magic The Gathering TCG"
              ]
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_plus_text_product_line_only`

Same filters plus `compound.must` with `text` on `product.name` when `BENCH_ATLAS_TEXT_QUERY` is non-blank after strip.

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Magic The Gathering TCG"
              ]
            }
          }
        ],
        "must": [
          {
            "text": {
              "path": "product.name",
              "query": "Dragon"
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_only_product_line_with_quantity`

Facet filters in `compound.filter` only (no `must` text on `product.name`).

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Magic The Gathering TCG"
              ]
            }
          },
          {
            "range": {
              "path": "inventory.quantity",
              "gte": 10
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_plus_text_product_line_with_quantity`

Same filters plus `compound.must` with `text` on `product.name` when `BENCH_ATLAS_TEXT_QUERY` is non-blank after strip.

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Magic The Gathering TCG"
              ]
            }
          },
          {
            "range": {
              "path": "inventory.quantity",
              "gte": 10
            }
          }
        ],
        "must": [
          {
            "text": {
              "path": "product.name",
              "query": "Dragon"
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_only_rare_product_lines`

Facet filters in `compound.filter` only (no `must` text on `product.name`).

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Union Arena",
                "Argent Saga TCG",
                "Warhammer Age of Sigmar Champions TCG"
              ]
            }
          }
        ]
      }
    }
  }
]
```

### `atlas_plus_text_rare_product_lines`

Same filters plus `compound.must` with `text` on `product.name` when `BENCH_ATLAS_TEXT_QUERY` is non-blank after strip.

```json
[
  {
    "$search": {
      "index": "bench_search_index",
      "compound": {
        "filter": [
          {
            "equals": {
              "path": "sellerKey",
              "value": "<SELLER_KEY>"
            }
          },
          {
            "in": {
              "path": "product.productLine",
              "value": [
                "Union Arena",
                "Argent Saga TCG",
                "Warhammer Age of Sigmar Champions TCG"
              ]
            }
          }
        ],
        "must": [
          {
            "text": {
              "path": "product.name",
              "query": "Dragon"
            }
          }
        ]
      }
    }
  }
]
```
