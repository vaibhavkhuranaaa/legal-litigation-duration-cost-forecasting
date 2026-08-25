# Offline demonstration

The release image builds the React interface and a deterministic SQLite seed containing only
nationwide portfolio totals, four aggregate procedural-cohort benchmarks, and release metadata.
It contains zero case-level rows, zero observed billing rows, no model artifact, no warehouse,
and no cloud credentials. The API opens the seed read-only.

Build with `docker build -t federal-civil-planner:local .` and run with
`docker run --rm -p 8080:8080 federal-civil-planner:local`. The interface and API are available
at `http://127.0.0.1:8080`; no network connection is needed after the image is built.

The demonstration is an operations aid, not legal advice. Historical aggregates are descriptive,
and staffing/budget outputs are deterministic synthetic sensitivities based only on user inputs.

The [public browser demo](https://vaibhavkhuranaaa.github.io/legal-litigation-duration-cost-forecasting/) uses the same approved aggregate constants and deterministic scenario equations. It contains no API credential, case-level row, model artifact, or live data connection.
