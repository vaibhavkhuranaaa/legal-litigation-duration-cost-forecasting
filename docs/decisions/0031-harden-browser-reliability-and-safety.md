# Harden browser reliability and safety

Status: implemented locally for M21. This decision authorizes no M22 work, data upload, deployment,
push, publication, or provider mutation.

## Decision

Treat the configured row-data origin and its manifest as untrusted input. Accept only HTTPS origins or
explicit loopback development origins, reject credentials, queries, fragments, redirects, unexpected
media types, incompatible manifests, and partition responses that do not prove byte-range service with
immutable caching. Require exact cross-origin allowlists at the local reference server.

Keep browser work bounded with a 256 MB DuckDB memory limit, one registered annual partition, disabled
full-HTTP fallback, bounded result and export ceilings, and explicit worker termination. A user cancel
or 10-second timeout replaces the worker, preserves the selected analytical scope, and announces
recovery in the same interface.

The aggregate cube remains independently usable when the row origin is absent or fails. Record-detail
focus moves into the opened panel and returns to its trigger on close. Native tables expose captions and
sort state, interactive targets meet the frozen audit floor, and the mobile command surface stacks below
420 pixels while wide row data stays inside its named horizontal scroller.

## Why

- Fail-closed origin and manifest checks prevent a configurable data endpoint from silently changing
  the publication contract or forcing whole-file transfers.
- Worker replacement is the only reliable browser-level cancellation boundary for all DuckDB-WASM
  query shapes.
- Preserving scope avoids turning operational recovery into an analytical state change.
- Keeping aggregate and row paths independent preserves a truthful rollback when row assets fail.
- Native semantics and explicit focus management support dense analytical use without another UI
  dependency.

## Alternatives rejected

- Cancel only the active DuckDB connection. Rejected because worker replacement gives one dependable
  recovery boundary across scan, group, sort, and export workloads.
- Allow arbitrary HTTP data origins. Rejected because non-loopback cleartext transport and ambient URL
  state weaken the publication boundary.
- Accept any successful Parquet response. Rejected because a status alone does not prove range support,
  stable sizing, immutable caching, or the expected media type.
- Prefetch every annual partition. Rejected because it violates the ordinary-transfer, memory, and
  zero-cost constraints.
- Add a new accessibility or component dependency. Rejected because native controls, table semantics,
  focus management, and the existing frozen checks satisfy the M21 scope.

## Evidence

- The M17 browser corpus passes all scan, group, sort, and export cancellation probes. Every restarted
  worker completes a following query, with zero termination or memory failures.
- The reference corpus records cold p95 of 67.9 ms and warm p95 of 10.7 ms, both below the frozen 3,000
  ms and 1,000 ms budgets.
- The final warm-cache network trace contains zero un-ranged or full-file Parquet GETs. A complete M17
  trace already established 206-only partition reads.
- Full schema and value scans cover all 5,008,334 private candidate rows and find zero disallowed public
  fields or values. The locked production dependency audit reports zero known vulnerabilities.
- Desktop and 390 by 844 mobile checks report zero frozen accessibility-rule findings, zero page-level
  overflow, contained table scrolling, and correct detail focus restoration.
- A diff-focused security review found one low-severity wildcard CORS issue in the local range server.
  Exact approved-origin reflection replaces the wildcard, and a hostile-origin request now receives
  HTTP 403 with no access-control header.
- The built Pages application plus one deterministic data candidate total 185,528,442 bytes, below the
  262,144,000-byte gate. The recurring infrastructure cost remains $0.
- The independent final interface review disposition is `ship`.

## Limitations

- Browser runtime evidence uses Chrome 151 on the declared desktop and mobile viewports. Standards-based
  build compatibility supplements this evidence; M22 must verify the exact public candidate URLs.
- The frozen accessibility rules and accessibility-tree review do not replace testing with every
  assistive technology and device combination.
- The private loopback server models required origin, cache, MIME, and range behavior. It is not proof
  of future public-host behavior.
- No row asset entered tracked Git or a public host. No upload, deployment, push, or publication occurred.

## Changed

- Added the reusable row-origin, manifest, and response contract validator and focused tests.
- Added partition preflight, disabled full HTTP fallback, set a 256 MB DuckDB limit, and made worker
  termination idempotent.
- Added user cancellation and timeout recovery with preserved analytical scope and live status.
- Added captions, sort state, detail focus management, target sizing, and narrow-mobile containment.
- Replaced wildcard local CORS with an exact approved-origin policy and updated architecture tests.
- Recorded private browser, accessibility, security, privacy, artifact, and cost evidence.

## Not done

- No M22 candidate was built, uploaded, activated, deployed, pushed, or published.
- No provider, repository, public asset, or live Pages state changed.
- No public-host range, cache, MIME, quota, or cost claim was made.
