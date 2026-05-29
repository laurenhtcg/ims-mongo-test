"""Populate bench_* collections from ``seller_inventory_raw`` via aggregation + ``$merge``."""

from __future__ import annotations

BATCH_SIZE = 1000

# Stages after ``$match`` on this batch's ``_id`` values (from a single keyset ``find``).
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
                "productLine": "$product.productLine.name",
                "set": "$product.customData.set.setName",
                "cardNumber": "$product.customData.identifiers.printedIdentifier",
                "language": {"$ifNull": ["$product.language.languageName", ""]},
                "printing": {"$ifNull": ["$product.customData.printing", ""]},
                "rarity": "$product.customData.rarity.rarityName",
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


def _merge_stage(database: str, collection_name: str) -> dict:
    return {
        "$merge": {
            "into": {"db": database, "coll": collection_name},
            "whenMatched": "replace",
            "whenNotMatched": "insert",
        }
    }


def _pipeline_for_batch(database: str, collection_name: str, batch_ids: list) -> list:
    return [{"$match": {"_id": {"$in": batch_ids}}}] + _SHAPE_STAGES + [
        _merge_stage(database, collection_name)
    ]


def merge_all() -> None:
    """Run the merge pipeline in batches so each ``bench_*`` collection receives the same documents."""
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
            filt: dict = {"_id": {"$gt": last_id}} if last_id is not None else {}
            batch_ids = [
                d["_id"]
                for d in source.find(filt, {"_id": 1}).sort("_id", 1).limit(BATCH_SIZE)
            ]
            if not batch_ids:
                break

            last_id = batch_ids[-1]
            for collection_name in targets:
                source.aggregate(
                    _pipeline_for_batch(db_name, collection_name, batch_ids),
                    allowDiskUse=True,
                )

            batch_num += 1
            print(f"Merged batch {batch_num} (through _id={last_id!r}) into {', '.join(targets)}")

        print("Finished merging all benchmark collections.")
    finally:
        client.close()
