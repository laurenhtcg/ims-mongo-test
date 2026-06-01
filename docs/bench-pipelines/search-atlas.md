# `search_atlas` pipelines (`bench_search`)

Supplementary reference: **exact aggregation pipeline** (as JSON) run by the **`search_atlas`** benchmark job on collection **`bench_search`**.

Atlas Search only (no MongoDB `$match`). Index: `bench_search_index`. Facet filters are built by `_atlas_filter_clauses_from_filter_test_params` (string lists → `in`; `quantity_min` → `range` on `inventory.quantity`).

## Conventions

- **`<SELLER_KEY>`** — replace with the `sellerKey` being benchmarked for that row.
- **Atlas index name** — set via environment variables documented on `mongo_bench.jobs.benchmarks.search_atlas` (e.g. `BENCH_SEARCH_COLLECTION`, `BENCH_SEARCH_ATLAS_INDEX`).
- **Name search query** — when a pipeline includes Atlas ``text`` on ``product.name``, the string comes from the ``text`` key in each merged benchmark case (`TEST_CASES` × `FILTER_TESTS` in ``benchmark_fixtures.py``), not from an environment variable.
- **`BenchmarkSession.timed`** (in `benchmark_session.py`) appends `{"$count": "c"}` to the pipeline for timing and count; that stage is **not** shown below.

---


## `FILTER_TESTS` parameter dicts (from `benchmark_fixtures.py`)

### `no_filters`

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

### `line_and_rarity`

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

### `line_and_languages`

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

### `rare_product_line`

```json
{
  "product_line": [
    "Warhammer Age of Sigmar Champions TCG"
  ]
}
```

## Pipelines per `FILTER_TESTS` row (representative `TEST_CASES` shapes)

Each benchmark row uses :meth:`mongo_bench.jobs.benchmarks.benchmark_session.BenchmarkSession.iter_test_cases`; below, **no-text** omits `text` (facet-only `$search`), **with-text** sets `text` to the sample query.

### `no_filters` — no `text` in case dict

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

### `no_filters` — with `text` = `Dragon`

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

### `multiple_filters_mtg` — no `text` in case dict

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

### `multiple_filters_mtg` — with `text` = `Dragon`

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

### `multiple_filters_pkm` — no `text` in case dict

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

### `multiple_filters_pkm` — with `text` = `Dragon`

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

### `line_and_rarity` — no `text` in case dict

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

### `line_and_rarity` — with `text` = `Dragon`

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

### `line_and_languages` — no `text` in case dict

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

### `line_and_languages` — with `text` = `Dragon`

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

### `product_line_only` — no `text` in case dict

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

### `product_line_only` — with `text` = `Dragon`

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

### `product_line_with_quantity` — no `text` in case dict

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

### `product_line_with_quantity` — with `text` = `Dragon`

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

### `rare_product_line` — no `text` in case dict

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

### `rare_product_line` — with `text` = `Dragon`

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
