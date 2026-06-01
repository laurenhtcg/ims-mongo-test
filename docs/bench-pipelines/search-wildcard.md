# `search_wildcard` pipelines (`bench_wildcard`)

Supplementary reference: **exact aggregation pipeline** (as JSON) run by the **`search_wildcard`** benchmark job on collection **`bench_wildcard`**.

MongoDB wildcard index: `bench_wildcard_sellerKey_paths`. Atlas Search index: `bench_text`. `$match` includes **only** fields present in each `FILTER_TESTS` entry (no sentinels).

## Conventions

- **`<SELLER_KEY>`** — replace with the `sellerKey` being benchmarked for that row.
- **Atlas index name** — set via environment variables documented on `mongo_bench.jobs.benchmarks.search_wildcard` (e.g. `BENCH_WILDCARD_COLLECTION`, `BENCH_ATLAS_SEARCH_INDEX`).
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

## Pipelines per CSV label

### `atlas_compound_sellerKey_name`

Same `$search` shape as `search_index` (different collection).

```json
[
  {
    "$search": {
      "index": "bench_text",
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

### `match_no_filters`

```json
[
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>"
    }
  }
]
```

### `atlas_plus_match_no_filters`

```json
[
  {
    "$search": {
      "index": "bench_text",
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
  },
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>"
    }
  }
]
```

### `match_multiple_filters_mtg`

```json
[
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Magic The Gathering TCG"
        ]
      },
      "product.set": {
        "$in": [
          "Commander Legends",
          "Aetherspiral"
        ]
      },
      "product.language": {
        "$in": [
          "English"
        ]
      },
      "product.printing": {
        "$in": [
          "Normal"
        ]
      }
    }
  }
]
```

### `atlas_plus_match_multiple_filters_mtg`

```json
[
  {
    "$search": {
      "index": "bench_text",
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
  },
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Magic The Gathering TCG"
        ]
      },
      "product.set": {
        "$in": [
          "Commander Legends",
          "Aetherspiral"
        ]
      },
      "product.language": {
        "$in": [
          "English"
        ]
      },
      "product.printing": {
        "$in": [
          "Normal"
        ]
      }
    }
  }
]
```

### `match_multiple_filters_pkm`

```json
[
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Pokémon TCG"
        ]
      },
      "product.set": {
        "$in": [
          "League & Championship Cards",
          "SWSH01: Sword & Shield Base Set"
        ]
      },
      "product.language": {
        "$in": [
          "English"
        ]
      },
      "product.printing": {
        "$in": [
          "Holofoil"
        ]
      }
    }
  }
]
```

### `atlas_plus_match_multiple_filters_pkm`

```json
[
  {
    "$search": {
      "index": "bench_text",
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
  },
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Pokémon TCG"
        ]
      },
      "product.set": {
        "$in": [
          "League & Championship Cards",
          "SWSH01: Sword & Shield Base Set"
        ]
      },
      "product.language": {
        "$in": [
          "English"
        ]
      },
      "product.printing": {
        "$in": [
          "Holofoil"
        ]
      }
    }
  }
]
```

### `match_line_and_rarity`

```json
[
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Magic The Gathering TCG"
        ]
      },
      "product.rarity": {
        "$in": [
          "Common",
          "Rare"
        ]
      }
    }
  }
]
```

### `atlas_plus_match_line_and_rarity`

```json
[
  {
    "$search": {
      "index": "bench_text",
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
  },
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Magic The Gathering TCG"
        ]
      },
      "product.rarity": {
        "$in": [
          "Common",
          "Rare"
        ]
      }
    }
  }
]
```

### `match_line_and_languages`

```json
[
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Magic The Gathering TCG"
        ]
      },
      "product.language": {
        "$in": [
          "English",
          "Japanese"
        ]
      },
      "product.printing": {
        "$in": [
          "Normal"
        ]
      }
    }
  }
]
```

### `atlas_plus_match_line_and_languages`

```json
[
  {
    "$search": {
      "index": "bench_text",
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
  },
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Magic The Gathering TCG"
        ]
      },
      "product.language": {
        "$in": [
          "English",
          "Japanese"
        ]
      },
      "product.printing": {
        "$in": [
          "Normal"
        ]
      }
    }
  }
]
```

### `match_product_line_only`

```json
[
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Magic The Gathering TCG"
        ]
      }
    }
  }
]
```

### `atlas_plus_match_product_line_only`

```json
[
  {
    "$search": {
      "index": "bench_text",
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
  },
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Magic The Gathering TCG"
        ]
      }
    }
  }
]
```

### `match_product_line_with_quantity`

```json
[
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Magic The Gathering TCG"
        ]
      },
      "inventory.quantity": {
        "$gte": 10
      }
    }
  }
]
```

### `atlas_plus_match_product_line_with_quantity`

```json
[
  {
    "$search": {
      "index": "bench_text",
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
  },
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Magic The Gathering TCG"
        ]
      },
      "inventory.quantity": {
        "$gte": 10
      }
    }
  }
]
```

### `match_rare_product_line`

```json
[
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Warhammer Age of Sigmar Champions TCG"
        ]
      }
    }
  }
]
```

### `atlas_plus_match_rare_product_line`

```json
[
  {
    "$search": {
      "index": "bench_text",
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
  },
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Warhammer Age of Sigmar Champions TCG"
        ]
      }
    }
  }
]
```
