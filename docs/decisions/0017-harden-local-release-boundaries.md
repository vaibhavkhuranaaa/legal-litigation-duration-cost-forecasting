# 0017: Harden local release boundaries

Status: accepted

## Decision

Admit only bounded requests, log metadata without content, verify acquisition and review artifacts
cryptographically, enforce archive and path budgets, and prevent model outputs from entering the
public tree. CI runs tests, static checks, secret scanning, frontend build, and dependency audit.

## Why

The public API and immutable loaders need explicit resource, provenance, and content boundaries even
for a local release. Security failures must be observable without logging matter content.

## Alternatives rejected

Framework defaults leave request and archive work unbounded. Shipping the complete analytics
environment would retain unnecessary cloud clients and a vulnerable SQL parser.

## Not done

No authentication, TLS termination, shared rate-limit store, centralized log platform, or signed
review identity is claimed because no internet deployment is authorized.

## Changed

Added admission control, audit metadata, archive/path/hash controls, artifact-bound promotion,
spreadsheet neutralization, public-output guards, scans, tests, and a minimal runtime dependency set.

## Consequences

The single-process local release has explicit, tested failure behavior. Distributed rate limiting,
authentication, TLS, centralized logging, and signed human-review attestations remain deployment
controls and are not implied by this offline release.
