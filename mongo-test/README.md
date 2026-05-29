# mongo-bench

Scaffold for running MongoDB search benchmark jobs. Populate and benchmark logic are stubs until you implement them.

## Layout

- `src/mongo_bench/` — Python package (`cli`, `config`, `db`, `jobs/…`); CLI includes `list-seller-keys` to print volume-tier sellers for `STATIC_BENCH_SELLER_KEYS`.
- `src/mongo_bench/jobs/populate/` — one module per long-running populate job (merge pipelines, `$merge` / `$out`, etc.); register new jobs in `jobs/__init__.py` (`POPULATE_JOBS`).
- `src/mongo_bench/resources/bench_collections.json` — canonical benchmark collection and index definitions (cite in test docs).
- `src/mongo_bench/bench_schema.py` — loads that JSON and applies indexes / Atlas Search indexes.
- `docs/benchmark-run-summary-*.md` — optional run notes; **`docs/bench-pipelines/`** — per-job aggregation pipeline JSON (regenerate with `PYTHONPATH=src python3 docs/bench-pipelines/generate_pipeline_docs.py`).
- `docker/Dockerfile` — application image (entrypoint `mongo-bench`).
- `docker-compose.yml` — MongoDB plus example job services.

## Local usage

Create a virtual environment, install the package in editable mode, then invoke the module or the console script.

Put connection settings in a **`.env`** file in the current working directory (usually `mongo-test/.env`) or next to the project root when using an editable install. The app loads it on first settings read via **python-dotenv** (existing shell variables are not overwritten). Optional: set **`MONGO_BENCH_DOTENV`** to an absolute path to a specific env file.

```bash
cd mongo-test
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m mongo_bench list-jobs
python -m mongo_bench init
python -m mongo_bench populate merge_all
python -m mongo_bench bench search_basic
```

After `populate merge_all`, regenerate static seller keys for `benchmark_fixtures.py`:

```bash
python -m mongo_bench list-seller-keys
```

Uses the same ``seller_keys_by_volume`` logic as the search benchmarks (default collection ``bench_index``, tier size from ``BENCH_SELLER_KEYS_PER_TIER``). See ``python -m mongo_bench list-seller-keys -h`` for ``--collection``, ``--per-tier``, and ``--skip-schema``.

With the console script:

```bash
mongo-bench list-jobs
mongo-bench list-seller-keys
```

## Docker usage

Compose **bakes your app into an image**; if you change Python code or `POPULATE_JOBS`, rebuild before `run` or you will still see old behavior (for example `Unknown populate job: 'merge_all'`):

```bash
docker compose build job-populate-default
```

### Connection settings (local Mongo in Compose vs external sandbox)

Job images read **`os.environ`** (`mongo_bench.config.load_settings`). Compose passes variables from the `environment:` block, which uses **substitution**: `MONGODB_URI: ${MONGODB_URI:-mongodb://mongo:27017}` means “use host/shell `MONGODB_URI` if set, else default to the `mongo` service”.

Docker Compose **automatically loads** a file named **`.env`** in the **same directory as `docker-compose.yml`** (`mongo-test/.env`) when resolving `${…}`. Put your sandbox URI and DB name there (do not commit real secrets). Exporting variables in your shell **overrides** the same keys from `.env`.

- **External MongoDB / Atlas sandbox** — use your `.env` (or exports), then run **without** starting the bundled DB:

  ```bash
  cd mongo-test
  docker compose run --no-deps --rm job-populate-default
  ```

  `--no-deps` skips the local `mongo` container and `depends_on` wait; the app still uses `MONGODB_URI` / `MONGODB_DB` from substitution.

- **Local Mongo from Compose** — leave `MONGODB_URI` unset in `.env` (or unset in shell) so the default `mongodb://mongo:27017` applies, start Mongo, then run:

  ```bash
  cd mongo-test
  docker compose up -d mongo
  docker compose run --rm job-populate-default
  ```

`populate merge_all` needs `seller_inventory_raw` and `product_catalog_raw` in the database given by `MONGODB_DB`.

Benchmark job (same env rules):

```bash
docker compose run --no-deps --rm job-bench-search-basic
```

To build and list jobs from the app image without touching data:

```bash
docker compose run --rm job-populate-default list-jobs
```

(That overrides the service default command; the populate service is normally used with its declared `command`.)

To use a custom command with the same image:

```bash
docker compose run --rm job-populate-default bench search_aggregation
```

## Benchmark collections (schema)

The **authoritative** definition of benchmark collection names, MongoDB indexes, and Atlas Search mappings is:

[`src/mongo_bench/resources/bench_collections.json`](src/mongo_bench/resources/bench_collections.json)

Reference that file (or commit hash + path) in test plans and write-ups so others can reproduce the same physical schema.

- **`bench_wildcard`** — wildcard MongoDB index on selected paths; Atlas Search indexes only explicit text-oriented fields.
- **`bench_index`** — compound MongoDB index; Atlas Search on explicit text fields only.
- **`bench_search`** — no collection-level indexes; Atlas Search index **`bench_search_dynamic_all`** uses **explicit** field mappings (`dynamic: false`) for the merge_all document shape (see `bench_collections.json`).

The **`search_index`**, **`search_wildcard`**, and **`search_atlas`** benchmarks print timings to stdout and, by default, each writes a **new** CSV per run:
``{job}_benchmark_{UTC timestamp}.csv`` in the working directory (e.g. ``search_index_benchmark_…csv``, ``search_wildcard_benchmark_…csv``, ``search_atlas_benchmark_…csv``).
Set **`BENCH_CSV_DIR`** to put those files in a folder, **`BENCH_CSV_PATH`** for a fixed path, **`BENCH_CSV_UNIQUE=0`**
for a stable ``{job}_benchmark.csv``, or **`BENCH_CSV=0`** to skip CSV. Use **`BENCH_WILDCARD_COLLECTION`** (default ``bench_wildcard``) for the wildcard job; **`BENCH_INDEX_COLLECTION`** for ``search_index``; **`BENCH_SEARCH_COLLECTION`** and **`BENCH_SEARCH_ATLAS_INDEX`** for ``search_atlas``. For ``search_atlas``, each ``FILTER_TESTS`` case runs twice in Atlas (filters-only then filters + name ``text``), using **`BENCH_ATLAS_TEXT_QUERY`** (default ``Dragon``) for the text arm.

Example analysis from benchmark CSVs: [`docs/benchmark-run-summary-2026-05-29.md`](docs/benchmark-run-summary-2026-05-29.md).

Loader and apply logic: [`src/mongo_bench/bench_schema.py`](src/mongo_bench/bench_schema.py) (`ensure_benchmark_collections`, `bench_collection_names`).

Commands:

- `mongo-bench init` — apply the schema once (collections/indexes/search as configured).
- `python -m mongo_bench.bench_schema` — same as `init` (useful to run the module directly). Optional: `--skip-search-indexes`. In Docker the image entrypoint is `mongo-bench`, so use  
  `docker compose run --rm --entrypoint python job-populate-default -m mongo_bench.bench_schema`  
  (add `--no-deps` when using an external `MONGODB_URI` from `.env`).
- `mongo-bench populate …` and `mongo-bench bench …` — **ensure the same schema by default** before running the job. Use `--skip-schema` to skip if you know the cluster is already prepared.

Atlas Search index creation uses PyMongo’s `createSearchIndexes` command and **requires MongoDB 7.0+ on Atlas** with Search enabled on the cluster. The bundled `docker-compose.yml` defaults `MONGO_BENCH_SKIP_SEARCH_INDEXES` to **1** when the variable is unset; set **`MONGO_BENCH_SKIP_SEARCH_INDEXES=0`** in `mongo-test/.env` (or your shell) for Atlas runs. If indexes still do not appear, check **stderr** for `mongo-bench:` lines: a **code 59** / “no such command” message means the host is not Atlas Search–capable (e.g. self-managed or wrong URI tier).

## Environment

See [.env.example](.env.example). `MONGODB_URI` and `MONGODB_DB` are read after optional `.env` loading in `mongo_bench.config` (see **Local usage**). `MONGO_BENCH_SKIP_SEARCH_INDEXES` skips Atlas Search index steps when using a non-Atlas deployment.

For **Docker job runs**, place the same variables in `mongo-test/.env` (next to `docker-compose.yml`) so Compose substitutes them into the container environment (see **Docker usage** above). If your `.env` lives elsewhere, run from `mongo-test` with `docker compose --env-file /path/to/.env run …` so interpolation picks up those values.
