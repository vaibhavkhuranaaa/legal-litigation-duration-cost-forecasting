# Security policy

## Supported release

Security fixes target the current `main` branch and the latest published container source.

## Reporting a vulnerability

Please use GitHub private vulnerability reporting when it is available for this repository. Do not include credentials, private court records, personal data, or active exploit details in a public issue.

Include the affected path or component, expected impact, reproduction conditions, and a minimal proof of concept that does not access third-party systems or data.

## Security boundaries

- No source dataset, warehouse, credential, model artifact, or generated row-level data asset belongs
  in tracked Git or the default aggregate release image.
- A future release may distribute only the M15-approved identifier-minimized statistical-record mart
  through a generated deployment artifact or explicit data pack after M21 security review and M22
  release approval.
- The public API enforces bounded request bodies, validation, security headers, and process-local rate limiting.
- The current shipped demonstration is aggregate-only and can run without network access.
- The product is not legal advice and does not release a duration forecast unless every declared gate passes.
