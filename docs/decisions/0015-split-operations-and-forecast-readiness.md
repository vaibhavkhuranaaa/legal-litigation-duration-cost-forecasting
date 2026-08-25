# Decision 0015: Split operations and forecast readiness

Status: accepted

## Decision

Expose separate readiness states for operations analytics, duration forecast, milestone events, and synthetic scenarios. Operations and scenarios may be ready while duration forecast and milestone events remain unavailable. Forecast requests return a typed refusal with failed gates and safe alternatives.

## Why

A single readiness flag would either hide usable operations functionality or misrepresent failed model capability. Capability-level readiness makes the boundary machine-readable.

## Alternatives rejected

- Returning HTTP errors for every forecast request would omit the evidence and safe alternatives users need.
- Marking the entire service unready would block verified portfolio and scenario workflows.
- Loading a failed model artifact would conflict with M7 promotion rules.

## Not done

No prediction endpoint, model artifact, event classifier, live warehouse connection, or identity-bearing response is enabled.

## Changed

FastAPI now provides eight versioned typed paths for health, readiness, portfolio, observed benchmarks, forecast refusal, milestone availability, synthetic scenarios, and provenance.
