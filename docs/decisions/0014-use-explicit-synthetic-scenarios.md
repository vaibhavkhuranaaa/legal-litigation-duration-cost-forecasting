# Decision 0014: Use explicit synthetic scenarios

Status: accepted

## Decision

Compute staffing and budget sensitivities only from bounded user-supplied assumptions. Return low, base, and high cases with hours, FTE, rate, multiplier, and budget units. Label every result `synthetic` and state that no observed cost data was used.

## Why

The product has no governed billing dataset. Deterministic assumption math supports operational discussion without inventing real legal-cost evidence.

## Alternatives rejected

- Deriving rates from court metadata would have no cost-data basis.
- Random simulation would add variability without evidence.
- Hiding default rates would make scenario totals unauditable.

## Not done

No real cost forecast, billing benchmark, probability distribution, or duration-model output enters the scenario.

## Changed

The scenario engine now validates inputs, uses decimal cents rounding, replays deterministically, and exposes every assumption beside results.
