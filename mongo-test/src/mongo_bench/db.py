"""MongoDB client wiring."""

from __future__ import annotations

from pymongo import MongoClient

from mongo_bench.config import load_settings


def get_client() -> MongoClient:
    """Return a Mongo client using ``MONGODB_URI`` from the environment (via ``load_settings``)."""
    settings = load_settings()
    return MongoClient(settings.mongodb_uri)
