# Canonical data dictionary

| Field | Type | Meaning | Rule |
| --- | --- | --- | --- |
| `source_record_identifier` | string | Immutable-source record lineage key | Source object identity plus source row position; not a cross-snapshot case key |
| `natural_case_identifier` | string | Documented circuit, district, office, and docket key | Promoted only when observed once in the current snapshot |
| `case_identifier` | string | Collision-free current-snapshot case key | Present only in the case mart; a future public seed will replace it with an opaque key |
| `source_row_number` | integer | One-based record position in the immutable source | Provenance only |
| `circuit_code` | string | FJC circuit code | Preserved from source |
| `district_code` | string | FJC district code | Preserved from source |
| `office_code` | string | FJC office code | Required component of the documented natural key |
| `docket_number` | string | Private source docket value | Excluded from public seed |
| `filed_date` | date | Case filing date | Required and not after snapshot cutoff |
| `filed_date_used_by_ao` | date | Filing date used for AO reporting | Reconciliation only, not survival duration |
| `terminated_date` | date or null | Observed termination date | Null for pending cases |
| `termination_date_used_by_ao` | date or null | Termination date used for AO reporting | Reconciliation only |
| `censoring_date` | date | Observation cutoff | Snapshot cutoff for pending cases |
| `analysis_end_date` | date | Termination date or censoring date | Required |
| `event_observed` | boolean | Termination observed by cutoff | False exactly when termination is not observed |
| `duration_days` | integer | Days from filing to termination or censoring | Nonnegative |
| `nature_of_suit_raw` | string | Source nature-of-suit value | Preserved for provenance |
| `nature_of_suit_code` | string or null | Exact codebook-supported code | Null for unsupported legacy codes |
| `nature_of_suit_family` | string | Versioned analytical family | Derived through tested map |
| `nature_of_suit_mapping_status` | string | `supported` or `unsupported` | Never inferred from numeric ranges |
| `identity_quality_status` | string | `canonical` or `collision` | Collision records remain in the exception mart |
| `source_record_count` | integer | Number of records sharing the natural identifier | Required and positive |
| `source_snapshot_cutoff` | date | Observation cutoff of the source snapshot | Required for censoring and provenance |

## Frozen serving-mart dictionary

This dictionary is authoritative for the locally built M16 mart and the M17 browser benchmark. The
mart remains private and is not approved for publication. "Record" retains the FJC statistical-record
grain and does not imply a unique legal case.

| Field | Type | Publication meaning | Publication rule |
| --- | --- | --- | --- |
| `release_record_key` | string | Opaque row key within one dataset version | HMAC-SHA-256, 128-bit output, private release secret |
| `circuit_code` | string | Circuit grouping | Approved analytical code only |
| `district_code` | string | District grouping | Approved analytical code only |
| `filed_month` | date | Filing month | First-day encoding; not an exact event day |
| `terminated_month` | date or null | Statistical termination month | First-day encoding; null when pending |
| `pending_status` | boolean | Pending at source cutoff | True exactly when no termination is observed |
| `event_observed` | boolean | Statistical termination observed | Never represented as legal outcome prediction |
| `duration_days` | integer | Filing to termination or censoring | Descriptive only and nonnegative |
| `nature_of_suit_code` | string or null | Approved exact codebook code | Null for unsupported source values |
| `nature_of_suit_family` | string | Governed analytical family | Versioned mapping only |
| `nature_of_suit_mapping_status` | string | Mapping support state | `supported` or `unsupported` |
| `jurisdiction_code` | string | Source jurisdiction category | Approved code only |
| `origin_code` | string | Source origin category | Approved code only |
| `procedural_cohort` | string | Governed administrative grouping | Descriptive, not a legal classification |
| `identity_quality_status` | string | `canonical` or `collision` | Collision records remain present and visibly labeled |
| `source_record_count` | integer | Records sharing the private natural key | Positive; reveals no source key |
| `recap_match_available` | boolean | Reviewed identity match exists | Exposes availability only, no RECAP identifier |
| `source_snapshot_cutoff` | date | Dataset observation cutoff | Same value as manifest snapshot |
| `dataset_version` | string | Immutable publication version | Required on every row or partition metadata |

Prohibited public fields include `source_record_identifier`, `natural_case_identifier`,
`case_identifier`, `source_row_number`, `office_code`, exact event and censoring dates,
`docket_number`, PACER or RECAP identifiers, names, judges, parties, attorneys, documents, text,
review labels, match evidence, credentials, private paths, and models.
