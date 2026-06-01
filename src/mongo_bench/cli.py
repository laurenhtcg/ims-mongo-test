"""CLI entrypoint for populate, benchmark, init, and utility commands."""

from __future__ import annotations

import argparse
import os
import sys

from mongo_bench.jobs import BENCHMARK_JOBS, POPULATE_JOBS


def _cmd_list_jobs(_args: argparse.Namespace) -> int:
    print("Populate jobs:")
    for name in sorted(POPULATE_JOBS):
        print(f"  - {name}")
    print("Benchmark jobs:")
    for name in sorted(BENCHMARK_JOBS):
        print(f"  - {name}")
    print("Other commands: list-seller-keys (see mongo-bench list-seller-keys -h)")
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    from mongo_bench.bench_schema import bench_collection_names, ensure_benchmark_collections
    from mongo_bench.config import load_settings
    from mongo_bench.db import get_client

    settings = load_settings()
    client = get_client()
    try:
        ensure_benchmark_collections(
            client,
            settings.mongodb_db,
            skip_search_indexes=True if args.skip_search_indexes else None,
        )
    finally:
        client.close()
    names = bench_collection_names()
    print(f"Benchmark schema applied on database {settings.mongodb_db!r}: {', '.join(names)}.")
    return 0


def _cmd_populate(args: argparse.Namespace) -> int:
    from mongo_bench.bench_schema import ensure_benchmark_collections_from_env
    from mongo_bench.db import get_client

    job = POPULATE_JOBS.get(args.name)
    if job is None:
        print(f"Unknown populate job: {args.name!r}", file=sys.stderr)
        return 1

    if not args.skip_schema:
        client = get_client()
        try:
            ensure_benchmark_collections_from_env(client)
        finally:
            client.close()

    print(f"Running populate job {args.name!r}.")
    job()
    return 0


def _cmd_bench(args: argparse.Namespace) -> int:
    from mongo_bench.bench_schema import ensure_benchmark_collections_from_env
    from mongo_bench.db import get_client

    job = BENCHMARK_JOBS.get(args.name)
    if job is None:
        print(f"Unknown benchmark job: {args.name!r}", file=sys.stderr)
        return 1

    if not args.skip_schema:
        client = get_client()
        try:
            ensure_benchmark_collections_from_env(client)
        finally:
            client.close()

    print(f"Running benchmark job {args.name!r}.")
    job()
    return 0


def _cmd_list_seller_keys(args: argparse.Namespace) -> int:
    """Print seller keys + tiers from :func:`seller_keys_by_volume` for updating STATIC_BENCH_SELLER_KEYS."""
    from mongo_bench.bench_schema import ensure_benchmark_collections_from_env
    from mongo_bench.config import load_settings
    from mongo_bench.db import get_client
    from mongo_bench.jobs.benchmarks.benchmark_fixtures import seller_keys_by_volume

    settings = load_settings()
    coll_name = args.collection or os.environ.get("BENCH_INDEX_COLLECTION", "bench_index")
    per_tier = args.per_tier if args.per_tier is not None else int(
        os.environ.get("BENCH_SELLER_KEYS_PER_TIER", "3")
    )

    client = get_client()
    try:
        if not args.skip_schema:
            ensure_benchmark_collections_from_env(client)
        coll = client[settings.mongodb_db][coll_name]
        rows = seller_keys_by_volume(coll, per_tier=per_tier)
    finally:
        client.close()

    if not rows:
        print(
            f"mongo-bench: no sellerKey groups in {settings.mongodb_db!r}.{coll_name!r}; "
            "populate the collection first.",
            file=sys.stderr,
        )
        return 1

    print(
        f"# db={settings.mongodb_db!r}  collection={coll_name!r}  "
        f"BENCH_SELLER_KEYS_PER_TIER={per_tier}  (same logic as search_index volume sampling)"
    )
    print("STATIC_BENCH_SELLER_KEYS: list[tuple[str, str]] = [")
    for key, tier in rows:
        print(f'    ("{key}", "{tier}"),')
    print("]")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mongo-bench")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-jobs", help="List registered populate and benchmark job names.")
    p_list.set_defaults(func=_cmd_list_jobs)

    p_init = sub.add_parser(
        "init",
        help="Ensure benchmark collections and indexes (see mongo_bench/resources/bench_collections.json).",
    )
    p_init.add_argument(
        "--skip-search-indexes",
        action="store_true",
        help="Skip Atlas Search index creation (same as MONGO_BENCH_SKIP_SEARCH_INDEXES=1).",
    )
    p_init.set_defaults(func=_cmd_init)

    p_pop = sub.add_parser("populate", help="Run a named populate job.")
    p_pop.add_argument("name", help="Job name, e.g. merge_all")
    p_pop.add_argument(
        "--skip-schema",
        action="store_true",
        help="Do not ensure collections/indexes before running the job.",
    )
    p_pop.set_defaults(func=_cmd_populate)

    p_bench = sub.add_parser("bench", help="Run a named benchmark job.")
    p_bench.add_argument("name", help="Job name, e.g. search_basic")
    p_bench.add_argument(
        "--skip-schema",
        action="store_true",
        help="Do not ensure collections/indexes before running the job.",
    )
    p_bench.set_defaults(func=_cmd_bench)

    p_sellers = sub.add_parser(
        "list-seller-keys",
        help=(
            "Print STATIC_BENCH_SELLER_KEYS-style lines using seller_keys_by_volume "
            "(same sampling as search benchmarks when not using static keys)."
        ),
    )
    p_sellers.add_argument(
        "--collection",
        metavar="NAME",
        default=None,
        help="Collection to scan (default: BENCH_INDEX_COLLECTION env or bench_index).",
    )
    p_sellers.add_argument(
        "--per-tier",
        type=int,
        default=None,
        metavar="N",
        help="Sellers per tier edge (default: BENCH_SELLER_KEYS_PER_TIER env or 3).",
    )
    p_sellers.add_argument(
        "--skip-schema",
        action="store_true",
        help="Do not ensure collections/indexes before querying.",
    )
    p_sellers.set_defaults(func=_cmd_list_seller_keys)

    ns = parser.parse_args(argv)
    return int(ns.func(ns))


if __name__ == "__main__":
    raise SystemExit(main())
