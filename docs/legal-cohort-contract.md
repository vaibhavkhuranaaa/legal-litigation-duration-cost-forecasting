# Legal Cohort and Outcome Contract

## Outcome

The modeled event is an FJC statistical termination. It does not establish a judgment on the merits, settlement, litigation completion for a client, fee amount, or legal strategy result. Estimates are operational planning aids and are not legal advice.

Duration starts at the FJC filing date and ends at the FJC termination date when observed. An unterminated record is right-censored at the source snapshot cutoff. The 365- and 730-day targets ask whether statistical termination occurred within each horizon.

## Intake procedural cohorts

The governed cohort is derived without removing cases:

| Cohort | Intake-known rule | Legal-operational use |
|---|---|---|
| Multidistrict litigation | Origin 6 or 13 | Separates transfer and MDL calendar behavior for diagnostics |
| Social Security review | Canonical nature family is `social_security` | Separates administrative-review matters |
| Ordinary original | Origin 1 and not Social Security | Ordinary-original filing benchmark |
| Other procedural origin | All remaining origins | Removed, remanded, reopened, transferred, and other routes |

These cohorts are descriptive and governed. They are not a post-outcome exclusion mechanism. In particular, MDL cases remain inside protocol version 3.

## Field timing

| Field | Timing classification | Protocol-v3 use |
|---|---|---|
| District, nature, jurisdiction, origin | Intake-known | Frozen features |
| Filing year and quarter | Intake-known | Frozen features |
| Title, section, subsection | Optional current-snapshot filing-law codes; stability unproven | Research only; forbidden from a later intake protocol absent immutable filing-time evidence |
| Jury-demand code | Mutable procedural field; a demand may follow the initial complaint | Diagnostic only; forbidden from intake protocols |
| Class-action code | Mutable procedural field with limited FJC quality control | Diagnostic only; forbidden from intake protocols |
| MDL docket code | Transfer/centralization field for an already-pending action | Diagnostic only; forbidden from intake protocols |
| Pro se and in-forma-pauperis codes | Mutable procedural fields with limited FJC quality control | Diagnostic only; forbidden from intake protocols |
| Arbitration at filing | Documented filing-time field but sparse and absent from the governed raw contract | Not a justified recovery feature by itself |
| Termination, duration, event, disposition | Outcome or post-filing | Evaluation only; forbidden from features |
| RECAP events, judge, parties | Post-filing or identity-bearing | Forbidden from intake features |

FJC documentation warns that quarterly records may be overwritten and that some administrative fields may change during a case with limited quality control. The annual civil files are termination-year extracts, not intake snapshots. A field is not promoted into an intake model until its filing-time availability and stability are demonstrated from official documentation or immutable historical snapshots. See [decision 0011](decisions/0011-reject-unproven-intake-fields.md).

## Refusal rule

If the estimator lacks validation-certified support for an intake pattern, the product abstains. It does not silently substitute a legally dissimilar case type or claim a matter-specific forecast.
