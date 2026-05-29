# `search_index` pipelines (`bench_index`)

Supplementary reference: **exact aggregation pipeline** (as JSON) run by the **`search_index`** benchmark job on collection **`bench_index`**.

MongoDB compound index: `bench_compound`. Atlas Search index: `bench_text`. `$match` uses sentinel `$ne: "XXXXXX"` on unused facet fields when any facet is set.

## Conventions

- **`<SELLER_KEY>`** — replace with the `sellerKey` being benchmarked for that row.
- **Atlas index name** and **text query** use this job’s Python defaults; override with environment variables documented on `mongo_bench.jobs.benchmarks.search_index` (e.g. `BENCH_INDEX_COLLECTION`, `BENCH_ATLAS_SEARCH_INDEX`, `BENCH_ATLAS_TEXT_QUERY`).
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

### `atlas_compound_sellerKey_name`

Single-stage Atlas text + `sellerKey` (no facet `$match`).

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

### `match_seller_only`

```json
[
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>"
    }
  }
]
```

### `atlas_plus_match_seller_only`

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
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
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
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
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
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
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
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
      }
    }
  }
]
```

### `match_sparse_filters`

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
        "$ne": "XXXXXX"
      },
      "product.language": {
        "$ne": "XXXXXX"
      },
      "product.printing": {
        "$ne": "XXXXXX"
      },
      "product.rarity": {
        "$in": [
          "Common",
          "Rare"
        ]
      },
      "product.type": {
        "$ne": "XXXXXX"
      }
    }
  }
]
```

### `atlas_plus_match_sparse_filters`

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
        "$ne": "XXXXXX"
      },
      "product.language": {
        "$ne": "XXXXXX"
      },
      "product.printing": {
        "$ne": "XXXXXX"
      },
      "product.rarity": {
        "$in": [
          "Common",
          "Rare"
        ]
      },
      "product.type": {
        "$ne": "XXXXXX"
      }
    }
  }
]
```

### `match_multiple_languages`

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
        "$ne": "XXXXXX"
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
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
      }
    }
  }
]
```

### `atlas_plus_match_multiple_languages`

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
        "$ne": "XXXXXX"
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
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
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
      },
      "product.set": {
        "$ne": "XXXXXX"
      },
      "product.language": {
        "$ne": "XXXXXX"
      },
      "product.printing": {
        "$ne": "XXXXXX"
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
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
      },
      "product.set": {
        "$ne": "XXXXXX"
      },
      "product.language": {
        "$ne": "XXXXXX"
      },
      "product.printing": {
        "$ne": "XXXXXX"
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
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
      "product.set": {
        "$ne": "XXXXXX"
      },
      "product.language": {
        "$ne": "XXXXXX"
      },
      "product.printing": {
        "$ne": "XXXXXX"
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
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
      "product.set": {
        "$ne": "XXXXXX"
      },
      "product.language": {
        "$ne": "XXXXXX"
      },
      "product.printing": {
        "$ne": "XXXXXX"
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
      },
      "inventory.quantity": {
        "$gte": 10
      }
    }
  }
]
```

### `match_rare_product_lines`

```json
[
  {
    "$match": {
      "sellerKey": "<SELLER_KEY>",
      "product.productLine": {
        "$in": [
          "Union Arena",
          "Argent Saga TCG",
          "Warhammer Age of Sigmar Champions TCG"
        ]
      },
      "product.set": {
        "$ne": "XXXXXX"
      },
      "product.language": {
        "$ne": "XXXXXX"
      },
      "product.printing": {
        "$ne": "XXXXXX"
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
      }
    }
  }
]
```

### `atlas_plus_match_rare_product_lines`

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
          "Union Arena",
          "Argent Saga TCG",
          "Warhammer Age of Sigmar Champions TCG"
        ]
      },
      "product.set": {
        "$ne": "XXXXXX"
      },
      "product.language": {
        "$ne": "XXXXXX"
      },
      "product.printing": {
        "$ne": "XXXXXX"
      },
      "product.rarity": {
        "$ne": "XXXXXX"
      },
      "product.type": {
        "$ne": "XXXXXX"
      }
    }
  }
]
```
