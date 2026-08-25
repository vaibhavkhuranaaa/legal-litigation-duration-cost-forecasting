# Source reconciliation

M5 treats FJC IDB as the federal civil population backbone, CourtListener RECAP as optional enrichment, and U.S. Courts Table C as aggregate validation. No RECAP row is assumed to identify an FJC case.

## Candidate boundary

The candidate rule is exact court, office, seven-digit docket core, and filing date. The district crosswalk covers all 94 federal districts and is versioned from the retained FJC codebook. Both sides must be unique. FJC natural-key collisions, malformed source rows, multiple candidates, parent-child ambiguity, and conflicting termination evidence are blocked.

Termination date, nature of suit, jurisdiction, PACER identifiers, and source-provided IDB identifiers are corroborators only. Names, parties, judges, and fuzzy text are not candidate keys. The public repository contains no source rows, review packets, or labels.

## Promotion gate

Candidates were held until a blinded human review passed all of these gates:

- reviewed precision of at least 99.5 percent;
- a two-sided 95 percent exact-binomial lower confidence bound of at least 99.5 percent;
- zero unresolved promoted collisions;
- reported coverage against both the collision-free eligible denominator and the complete FJC statistical-record population;
- row-level rule, source snapshot, identifier, reviewer, and disposition provenance.

The private packet uses a deterministic 800-item sample. It first includes marginal representation across courts, five-year filing bands, and termination-evidence bands, then fills by a stable order. Every uncertain or disputed item requires adjudication. Any false match fails the current 800-item gate and triggers rule review or sample expansion.

## Aggregate validation

AO Table C is aligned to the 12 months ending March 31, 2026. FJC filing and termination cohorts use the dates designated for AO reporting; pending is the full status-S stock at the reporting cutoff. Pre-2010 pending records remain in the complete-population comparison and are bridged explicitly to the product's 2010-plus scope.

National count differences must be no more than 0.5 percent. District differences use a 2 percent diagnostic tolerance and never override the national gate. Every out-of-tolerance district requires a reason code and disposition, including known multidistrict-litigation inventory effects. Publication-version lag is a limitation, not proof of any row-level difference.

The measured complete FJC snapshot has 339,754 filings, 276,113 terminations, and 462,223 pending records for this comparison. Relative differences from Table C are 0.041 percent, 0.150 percent, and zero, respectively. All three national comparisons pass the predeclared threshold. This validates aggregate definitions; it does not establish cross-source identity.

One district diagnostic is outside the 2 percent tolerance: Southern District of Texas terminations differ by 214 records, or 2.71 percent. No retained evidence resolves the row-level cause. The cell is retained with an unresolved district-definition or multidistrict-litigation review reason and is not averaged away. It does not override the separately predeclared national gate.

## Current status

Governed review labeled all 800 sampled candidates as true matches. Reviewed precision is 100 percent and the two-sided 95 percent exact-binomial lower bound is 99.54 percent, above the predeclared 99.5 percent threshold. The exact rule therefore promoted 2,065,537 one-to-one matches with zero unresolved collisions.

Coverage is 44.46 percent of 4,645,719 collision-free cases and 41.24 percent of all 5,008,334 statistical records. Private coverage evidence also reports all 94 districts, 17 filing years, and 14 canonical nature families. Coverage is descriptive and was not increased by weakening the precision rule. Review validates the exact identity rule; it does not establish unmatched completeness or RECAP event quality. No CourtListener API was called and no cloud resource was queried or changed.
