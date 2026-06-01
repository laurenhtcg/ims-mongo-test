"""
Populate bench_* collections from ``seller_inventory_raw`` via aggregation + batched upserts.
This can only be run against sandbox MongoDB.
"""

from __future__ import annotations

from pymongo import ReplaceOne

BATCH_SIZE = 1000

# Stages after ``$sort`` / ``$limit`` (keyset batching on ``_id``).
_SHAPE_STAGES = [
    {
        "$lookup": {
            "from": "product_catalog_raw",
            "localField": "productId",
            "foreignField": "_id",
            "as": "product",
        }
    },
    {
        "$project": {
            "_id": 1,
            "sellerKey": 1,
            "pamKey": 1,
            "inventory": {
                "quantity": "$quantity",
                "reserveQuantity": "$reserveQuantity",
                "lastUpdated": "$lastUpdated",
            },
            "product": {"$arrayElemAt": ["$product", 0]},
        }
    },
    {
        "$project": {
            "_id": 1,
            "sellerKey": 1,
            "pamKey": 1,
            "inventory": 1,
            "product": {
                "id": "$product._id",
                "name": "$product.name",
                "productLine": {"$ifNull": ["$product.productLine.name", ""]},
                "set": {"$ifNull": ["$product.customData.set.setName", ""]},
                "cardNumber": "$product.customData.identifiers.printedIdentifier",
                "language": {"$ifNull": ["$product.language.languageName", ""]},
                "printing": {"$ifNull": ["$product.customData.printing", ""]},
                "rarity": {"$ifNull": ["$product.customData.rarity.rarityName", ""]},
                "type": {
                    "$ifNull": [
                        "$product.productType.name",
                        "$product.customData.productTypes.baseType",
                        "Card Single",
                    ]
                },
            },
        }
    },
]


def _batched_shape_pipeline(last_id: object | None) -> list:
    head: list = []
    if last_id is not None:
        head.append({"$match": {"_id": {"$gt": last_id}}})
    head.extend([{"$sort": {"_id": 1}}, {"$limit": BATCH_SIZE}])
    return head + _SHAPE_STAGES


def _add_attributes(doc: dict) -> dict:
    """Add attributes to the document."""

    doc["attributes"] = [
        {
            "key": "rarity",
            "value": doc["product"]["rarity"],
        },
        {
            "key": "type",
            "value": doc["product"]["type"],
        },
        {
            "key": "language",
            "value": doc["product"]["language"],
        },
        {
            "key": "printing",
            "value": doc["product"]["printing"],
        },
        {
            "key": "productLine",
            "value": doc["product"]["productLine"],
        },
        {
            "key": "set",
            "value": doc["product"]["set"],
        },
        {
            "key": "name",
            "value": doc["product"]["name"],
        },
    ]

    return doc


def merge_all() -> None:
    """Run the shape pipeline in batches; upsert each document into every ``bench_*`` collection."""
    from mongo_bench.bench_schema import bench_collection_names
    from mongo_bench.config import load_settings
    from mongo_bench.db import get_client

    settings = load_settings()
    db_name = settings.mongodb_db
    targets = bench_collection_names()

    client = get_client()
    try:
        db = client[db_name]
        source = db["seller_inventory_raw"]

        last_id: object | None = None
        batch_num = 0
        while True:
            docs = list(
                source.aggregate(_batched_shape_pipeline(last_id), allowDiskUse=True)
            )
            if not docs:
                break

            last_id = docs[-1]["_id"]
            ops = [
                ReplaceOne({"_id": d["_id"]}, _add_attributes(d), upsert=True)
                for d in docs
            ]
            if ops:
                for collection_name in targets:
                    db[collection_name].bulk_write(ops, ordered=False)

            batch_num += 1
            print(
                f"Upserted batch {batch_num} (through _id={last_id!r}) into {', '.join(targets)}"
            )

            if batch_num >= 300:
                break

        print("Finished upserting all benchmark collections.")
    finally:
        client.close()
