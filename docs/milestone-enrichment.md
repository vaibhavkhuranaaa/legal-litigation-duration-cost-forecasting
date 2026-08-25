# Milestone enrichment availability

The retained RECAP bulk source supports reviewed docket identity and operational metadata, not docket events. It lacks docket-entry number and description fields, so event-family extraction is disabled.

| Measure | Result | Method | Decision | Limitation |
|---|---:|---|---|---|
| Promoted matched cases | 2,065,537 | Governed exact FJC and RECAP reconciliation | Docket provenance available | Match review does not establish event quality |
| Collision-free match coverage | 44.46% | Promoted matches divided by 4,645,719 collision-free cases | Coverage disclosed | Unmatched cases remain valid FJC records |
| Event-entry candidates | 0 | Required `entry_number`, `date_filed`, and `description` schema check | Disable event enrichment | Source is docket metadata only |
| Unsupported inferred events | 0 | Fail-closed availability contract | Pass | No event precision or recall can be claimed |

API consumers receive `event_unavailable`, the missing field list, source cutoff, and an observed-data fallback. No duration estimate is updated.
