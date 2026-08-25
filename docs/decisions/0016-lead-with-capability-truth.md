# Decision 0016: Lead with capability truth

Status: accepted

## Decision

Use a staged operations interface that keeps capability readiness visible above both workflows. Observed portfolio measures, forecast refusal, docket-event unavailability, and synthetic scenario labels retain distinct visual and textual treatment.

## Why

Portfolio users need governed workload evidence, while matter-planning users need a safe way to test their own resource assumptions. A persistent capability ribbon prevents either workflow from obscuring the failed duration and event gates.

## Alternatives rejected

- A conventional dashboard with forecast cards would imply a capability that did not pass M7.
- A single blended evidence view would make observed measures and synthetic assumptions harder to distinguish.
- Hiding unavailable capabilities would weaken the audit trail.

## Not done

The interface does not predict duration, infer docket events, estimate real legal costs, provide legal advice, or connect to a live warehouse.

## Changed

The React and TypeScript client now provides responsive portfolio and matter-planning workflows, an observed cohort comparator, deterministic synthetic scenarios, evidence export, loading and connection-error states, and explicit provenance and refusal language.
