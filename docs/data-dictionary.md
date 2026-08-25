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
