# Local release cost estimate

Incremental paid infrastructure cost for this release is $0. It was built and verified locally;
no cloud mutation, deployment, paid service, or live warehouse query was performed.

The scenario engine's dollar outputs are not this estimate. They are synthetic sensitivities made
from user-entered hours, rates, matter counts, and multipliers and use zero observed billing data.

A future hosted cost estimate must be prepared from an approved architecture, traffic envelope,
retention policy, regional requirements, and current vendor prices. This local result must not be
extrapolated into a hosted operating-cost claim.

## Row-level operating envelope

The row release retains a recurring infrastructure ceiling of $0 for its declared portfolio usage.
GitHub Pages serves the application and Cloudflare R2 plus a read-only Worker serve the immutable row
inventory. M17 recorded the local and read-only host evidence; this is not a permanent price or
behavior guarantee.

M17 records compressed bytes, query transfer, cache behavior, projected monthly bandwidth, build
minutes, storage, and request counts. M22 published 185,759,334 bytes in R2 and verified every object
through the production Worker. Final-upload Class A operations were 103; conservative bounds,
including retries, remain below 1,000 Class A operations and below 10,000 Class B and Worker requests.
At 0.186 GB of Standard storage, measured usage remains within the current included allowances and
reconciled incremental cost is $0. Provider aggregate bucket statistics lagged the exact manifest
verification and are not used as the authoritative byte count. Approaching a free-tier limit causes a release or feature pause, not automatic paid
overage, account provisioning, or provider migration.
