# Decision 0011: Reject unproven intake fields and preserve the M7 source gate

Status: accepted

## Context

Protocol version 3 failed its rolling development gates without reading the sealed final holdout. A later protocol could add a field only if primary legal and data documentation establishes that the value is available and stable when the intake estimate is made.

The FJC civil codebook describes title, section, and subsection as optional; identifies jury demand and class-action indicators; describes arbitration as a filing-time field; and names the MDL docket field without assigning it a filing-time timestamp. The FJC research guide warns that quarterly records can be overwritten as courts alter information and specifically identifies jury, pro se, in-forma-pauperis, and class-action values as fields that may change during a case and receive limited quality control.

Primary procedural sources reinforce the timing problem. Federal Rule of Civil Procedure 38 permits a jury demand after the initial complaint, and the Judicial Panel on Multidistrict Litigation creates an MDL by transferring already-pending actions. FJC annual civil datasets are termination-year extracts, not historical intake snapshots.

## Decision

Do not add title, section, subsection, jury demand, class action, MDL docket, pro se, or in-forma-pauperis values to an intake estimator from the retained current-state snapshot. Current-snapshot presence is not filing-time evidence. Arbitration remains documented as filing-time but is too sparse and was not carried through the governed raw contract; it is not a justified recovery feature by itself.

Do not declare a later protocol merely to retune support against already-inspected development outcomes. The validation-only marginal support diagnostic cannot satisfy both unchanged gates: in the pandemic-era fold a 10 percent marginal certification threshold covers about 34 percent of cases, below the required 80 percent, while looser support leaves material slice error.

Keep protocol versions 1, 2, and 3 as negative evidence. Keep the April through June 2024 final outcomes sealed. Require both a predeclared development policy with credible independent evidence and an official case-level FJC cutoff on or after June 30, 2026 before any final score.

## Consequences

The current public data cannot support the required nationwide individual duration estimate without either leakage, post-outcome cohort removal, or weaker gates. None is permitted. M8 through M14 remain dependency-blocked. The next valid source action is to acquire a changed FJC cumulative object through a new immutable manifest, confirm its stated cutoff, rebuild versioned M3 through M6 artifacts, and only then execute an authorized frozen evaluation.
