# `search_attributes` pipelines (`bench_attributes`)

Supplementary reference: **exact aggregation pipeline** (as JSON) run by the **`search_attributes`** benchmark job on collection **`bench_attributes`**.

MongoDB compound index: `bench_attributes_compound` (``sellerKey``, ``attributes.key``, ``attributes.value``, ``inventory.quantity``). Atlas Search index: `bench_text`. ``$match`` uses ``$elemMatch`` on ``attributes`` for each facet dimension present in `FILTER_TESTS` (same keys as `merge_all._add_attributes`).

## Conventions

- **`<SELLER_KEY>`** — replace with the `sellerKey` being benchmarked for that row.
- **Atlas index name** — set via environment variables documented on `mongo_bench.jobs.benchmarks.search_attributes` (e.g. `BENCH_ATTRIBUTES_COLLECTION`, `BENCH_ATLAS_SEARCH_INDEX`).
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

Same `$search` shape as `search_index` (different collection / index definitions in `bench_collections.json`).

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
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Magic The Gathering TCG"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "set",
              "value": {
                "$in": [
                  "Commander Legends",
                  "Aetherspiral"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "language",
              "value": {
                "$in": [
                  "English"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "printing",
              "value": {
                "$in": [
                  "Normal"
                ]
              }
            }
          }
        }
      ]
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
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Magic The Gathering TCG"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "set",
              "value": {
                "$in": [
                  "Commander Legends",
                  "Aetherspiral"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "language",
              "value": {
                "$in": [
                  "English"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "printing",
              "value": {
                "$in": [
                  "Normal"
                ]
              }
            }
          }
        }
      ]
    }
  }
]
```

### `match_multiple_filters_pkm`

```json
[
  {
    "$match": {
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Pokémon TCG"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "set",
              "value": {
                "$in": [
                  "League & Championship Cards",
                  "SWSH01: Sword & Shield Base Set"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "language",
              "value": {
                "$in": [
                  "English"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "printing",
              "value": {
                "$in": [
                  "Holofoil"
                ]
              }
            }
          }
        }
      ]
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
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Pokémon TCG"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "set",
              "value": {
                "$in": [
                  "League & Championship Cards",
                  "SWSH01: Sword & Shield Base Set"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "language",
              "value": {
                "$in": [
                  "English"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "printing",
              "value": {
                "$in": [
                  "Holofoil"
                ]
              }
            }
          }
        }
      ]
    }
  }
]
```

### `match_line_and_rarity`

```json
[
  {
    "$match": {
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Magic The Gathering TCG"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "rarity",
              "value": {
                "$in": [
                  "Common",
                  "Rare"
                ]
              }
            }
          }
        }
      ]
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
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Magic The Gathering TCG"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "rarity",
              "value": {
                "$in": [
                  "Common",
                  "Rare"
                ]
              }
            }
          }
        }
      ]
    }
  }
]
```

### `match_line_and_languages`

```json
[
  {
    "$match": {
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Magic The Gathering TCG"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "language",
              "value": {
                "$in": [
                  "English",
                  "Japanese"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "printing",
              "value": {
                "$in": [
                  "Normal"
                ]
              }
            }
          }
        }
      ]
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
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Magic The Gathering TCG"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "language",
              "value": {
                "$in": [
                  "English",
                  "Japanese"
                ]
              }
            }
          }
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "printing",
              "value": {
                "$in": [
                  "Normal"
                ]
              }
            }
          }
        }
      ]
    }
  }
]
```

### `match_product_line_only`

```json
[
  {
    "$match": {
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Magic The Gathering TCG"
                ]
              }
            }
          }
        }
      ]
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
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Magic The Gathering TCG"
                ]
              }
            }
          }
        }
      ]
    }
  }
]
```

### `match_product_line_with_quantity`

```json
[
  {
    "$match": {
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Magic The Gathering TCG"
                ]
              }
            }
          }
        },
        {
          "inventory.quantity": {
            "$gte": 10
          }
        }
      ]
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
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Magic The Gathering TCG"
                ]
              }
            }
          }
        },
        {
          "inventory.quantity": {
            "$gte": 10
          }
        }
      ]
    }
  }
]
```

### `match_rare_product_line`

```json
[
  {
    "$match": {
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Warhammer Age of Sigmar Champions TCG"
                ]
              }
            }
          }
        }
      ]
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
      "$and": [
        {
          "sellerKey": "<SELLER_KEY>"
        },
        {
          "attributes": {
            "$elemMatch": {
              "key": "productLine",
              "value": {
                "$in": [
                  "Warhammer Age of Sigmar Champions TCG"
                ]
              }
            }
          }
        }
      ]
    }
  }
]
```
