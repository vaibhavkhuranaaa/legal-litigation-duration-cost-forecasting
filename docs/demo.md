# Distribution modes

The release image builds the React interface, a deterministic SQLite seed, and a versioned
full-population analytical cube. The cube is generated from all 5,008,334 governed records and
contains exact national and marginal totals plus supported district, nature-family, filing-year,
and pending-age aggregates. Cells below 200 records are withheld. It contains zero case-level rows,
zero observed billing rows, no model artifact, no warehouse, and no cloud credentials.

For an offline release, build with `docker build -t federal-civil-planner:local .` and run with
`docker run --rm -p 8080:8080 federal-civil-planner:local`. The interface and API are available
at `http://127.0.0.1:8080`; no network connection is needed after the image is built.

The demonstration is an operations aid, not legal advice. Historical aggregates are descriptive,
and staffing/budget outputs are deterministic synthetic sensitivities based only on user inputs.

The [public portfolio intelligence dashboard](https://vaibhavkhuranaaa.github.io/legal-litigation-duration-cost-forecasting/) uses the same approved cube and deterministic scenario equations, plus the governed row-data origin for bounded record exploration. It contains no API credential, source identifier, model artifact, or private-warehouse connection.

## Row-level distribution

The public mode keeps the aggregate cube for initial rendering and rollback, then queries an
immutable, identifier-minimized Parquet data pack through DuckDB-WASM. The data pack is generated for
the approved production row-data origin and remains outside tracked Git.
Application, manifest, semantic registry, and partitions share compatible version identifiers.

The offline container remains aggregate-only unless a separately downloaded, compatible data pack is
mounted by the user. A missing, incompatible, or unavailable data pack falls back to aggregate views
with a clear explanation. It never causes the container to reach the private warehouse.
