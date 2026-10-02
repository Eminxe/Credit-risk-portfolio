# Verified GitHub execution

- Repository: [Eminxe/Credit-risk-portfolio](https://github.com/Eminxe/Credit-risk-portfolio).
- Tested source commit: [d9f52d0](https://github.com/Eminxe/Credit-risk-portfolio/commit/d9f52d0245b948d3a9ea5dbf66fee74dc00a7688).
- [Push checks](https://github.com/Eminxe/Credit-risk-portfolio/actions/runs/37003931160): success.
- [Full real-data validation](https://github.com/Eminxe/Credit-risk-portfolio/actions/runs/37004011370): success, 2026-10-02.
- Jobs: tests and real-data, both successful.

Checks: Ruff, 16 unit tests, Docker build, PostgreSQL 16, all six real-source pipelines,
independent calculations, SQL row counts/idempotence, executed notebook and authenticated
Jupyter HTTP 200. The fresh SQL database held 30,000 rows in each core table and 138 aggregate rows.
Printed Case 01 holdout metrics reproduced the local report (ROC-AUC 0.782006, Brier 0.135352).

## Downloadable run evidence

Open the full run above and download **verified-case-outputs** from Artifacts.

- Artifact ID: 11224444730
- Size: 8,846,324 bytes
- SHA-256: b068a1d3f93a1d6e2cd0f5277eaecf709fbf0b0fb6288741ada8f84a938e5290
- GitHub retention expiry: 2026-12-31T11:58:52Z

Published outputs/ evidence is the reviewed local run from 2026-10-01. The downloadable
artifact holds the independent Linux runner execution. File hashes may differ across runs;
lineage is checked within each run. No claim of bit-for-bit cross-platform binary identity is made.
Later documentation-only commits do not alter the tested analytical code.
