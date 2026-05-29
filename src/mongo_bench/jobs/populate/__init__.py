"""Populate jobs: long-running seeds, often aggregation pipelines with ``$merge`` / ``$out``.

Add one module per job and register it in ``mongo_bench.jobs.POPULATE_JOBS``.
"""

from mongo_bench.jobs.populate.merge_all import merge_all
from mongo_bench.jobs.populate.seed_orders import seed_orders
from mongo_bench.jobs.populate.seed_users import seed_users

__all__ = ["merge_all", "seed_orders", "seed_users"]
