# Semantic metrics

Registry `metrics.v1` is the semantic source for labels, formulas, formats, tooltips, support rules, definitions, and exports.

| Measure | Definition | Format | Limitation | Export label |
| --- | --- | --- | --- | --- |
| Statistical records | Count of governed FJC statistical records in scope. | integer | Collision-labeled rows remain included. | Statistical records |
| Collision-free records | Records whose private natural identifier occurs once in the snapshot. | integer | Snapshot uniqueness is not cross-system identity certainty. | Collision-free records |
| Pending records | Records without observed statistical termination at the source cutoff. | integer | Pending status reflects the source snapshot, not current docket status. | Pending records |
| Observed terminations | Records with statistical termination observed by the source cutoff. | integer | No outcome direction or prediction is implied. | Observed terminations |
| RECAP-matched records | Records with a reviewed one-to-one RECAP identity match. | integer | Unmatched records may still have public dockets outside the retained match rule. | RECAP-matched records |
| Mapped nature records | Records with exact codebook-supported nature-of-suit mapping. | integer | Support is specific to the versioned mapping. | Mapped nature records |
| Average observed duration | Mean filing-to-termination days among records with observed statistical termination. | days_1 | Not a forecast for an open or future matter. | Average observed duration days |
| Pending share | Pending records divided by all statistical records in scope. | percent_1 | Not a probability that a new filing will remain open. | Pending share |
| RECAP match coverage | RECAP-matched records divided by all statistical records in scope. | percent_1 | No minimum coverage target applies. | RECAP match coverage |
| Follow-up days | Total filing-to-termination or filing-to-cutoff days across records in scope. | integer | Additive exposure measure, not average time to disposition. | Follow-up days |
| Average pending age | Mean filing-to-cutoff days among pending records in scope. | days_1 | Not remaining duration or predicted time to termination. | Average pending age days |

## Query contexts

| Context | Measures | Compatible dimensions | Support rule |
| --- | ---: | ---: | --- |
| Portfolio | 9 | 16 | At least 200 statistical records |
| Filing cohorts | 5 | 15 | At least 200 statistical records |
| Pending inventory | 3 | 14 | At least 200 pending records |

Queries accept registered identifiers and operators only. Values use bound parameters, results are capped at 10,000 rows, and raw SQL is not accepted from URL or user input.

Historical measures remain descriptive. Duration and age measures are not forecasts, and statistical records are not guaranteed unique legal cases.
