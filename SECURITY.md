# Security policy

## Supported release

Security fixes target the current `main` branch and the latest published container source.

## Reporting a vulnerability

Please use GitHub private vulnerability reporting when it is available for this repository. Do not include credentials, private court records, personal data, or active exploit details in a public issue.

Include the affected path or component, expected impact, reproduction conditions, and a minimal proof of concept that does not access third-party systems or data.

## Security boundaries

- No source dataset, warehouse, credential, model artifact, or case-level demonstration row belongs in this repository or release image.
- The public API enforces bounded request bodies, validation, security headers, and process-local rate limiting.
- The shipped demonstration is aggregate-only and can run without network access.
- The product is not legal advice and does not release a duration forecast unless every declared gate passes.
