# Execution status — 2026-10-01

## Verified locally

- WSL2 Ubuntu and Docker Desktop Linux engine 29.8.0 are running.
- Python 3.12 analytical Docker image built successfully, including a second build from
  requirements-linux.lock with a pinned Python base digest.
- PostgreSQL 16.15 is healthy; its image digest is pinned.
- JupyterLab is healthy and an authenticated /api/status request returned HTTP 200.
  A startup filename that shadowed the jupyter_server package was fixed.
- VS Code extensions installed: Python, Jupyter, WSL and Dev Containers.
  The devcontainer configuration selects container Python 3.12.
- Ubuntu's system Python is 3.14.4 and Git is 2.53.0. System Python was preserved.
- All six real-data cases executed successfully. No synthetic analysis outputs.
- Ruff passed; 16 unit tests passed (the suite has since grown; see CI for the current count).
- Independent source and arithmetic checks passed for all six cases.
- SQL loaded 30,000 records into each core table. Current additional-case versions have
  138 aggregate records in total; earlier versions are retained separately.
- Repeat SQL loads verified idempotence.
- notebooks/01_06_casebook.ipynb executed using a separate Jupyter kernel; HTML exported.
- Employer and Russian guides rendered in Edge. Three HTML documents had no broken images
  or page overflow at the checked desktop viewport; employer mobile preview also inspected.
- Reviewed credit figures and the new campaign, experiment and vintage figures.
  Noneligible vintage gaps are preserved rather than bridged with lines.

## Methodology corrections and findings

- Credit model selection stayed on development OOF log loss. Reserved holdout: 6,006 rows;
  selected boosting ROC-AUC 0.782006, Brier 0.135352, log loss 0.429338.
- AUC interval 0.7669–0.7965 uses 500 group-bootstrap draws with the fitted model fixed.
- Preserved original 12-month negative-NPV scenario; added one-month existing-account
  comparison and moved monetary sensitivity grids into configuration.
- Campaign duration/current-campaign fields excluded. Identical retained-feature groups
  are purged across selection and holdout boundaries and within calibration folds.
  Validation after purging has 9,000 rows. Holdout remains 9,043 rows; AUC remains 0.592325.
- Hillstrom: all 64,000 assigned customers; pointwise Welch intervals and Holm correction.
- LendingClub: 39,786 policy-eligible loans, 5,670 charged off; 42 of 55 monthly cohorts
  meet reporting thresholds. The snapshot cannot support true monthly roll rates.

## Delivery and remaining external actions

- English overview: PORTFOLIO_EN.md and outputs/portfolio_en.html.
- Russian explanation with formulas/code mapping: РАЗБОР_RU.md and outputs/explanation_ru.html.
- Full executed evidence: outputs/casebook.html.
- Packaging script excludes .env, raw datasets, caches and the old three-case notebook.
  package_receipt.json and outputs/artifact_index.json record archive/content hashes.
- The user's old parent ZIP is preserved; current archive is in deliverables/.
- Git initialized; no remote repository configured. CI YAML is prepared, but no remote CI run,
  commit publication or GitHub deployment is claimed.
- No regulatory validation, actual bank P&L, future-period credit validation, causal limit
  response or observed monthly roll rates is claimed.

Machine-readable receipts: outputs/validation_run.json, verification.json,
verification_additional.json and infrastructure_verification.json.
These supersede earlier notes reporting Docker and Jupyter access as blocked.

## GitHub publication — 2026-10-02

Published source and selected aggregate evidence to Eminxe/Credit-risk-portfolio.
See GitHub Actions for current remote validation results; the checks above describe local execution.

## Remote validation — completed 2026-10-02

[Full GitHub Actions run](https://github.com/Eminxe/Credit-risk-portfolio/actions/runs/37004011370) succeeded for commit
d9f52d0245b948d3a9ea5dbf66fee74dc00a7688. Both jobs succeeded: tests and real-data.
All six studies downloaded their sources afresh, then passed independent reconciliation,
SQL load/idempotence, notebook execution and authenticated Jupyter checks. The fresh SQL database
contains 30,000 rows in each core table and 138 aggregate rows. Artifact verified-case-outputs
was uploaded (8,846,324 bytes). See CI_RESULT.md for the artifact digest and expiry.
Earlier local-only/pending publication notes above describe the previous state and are superseded.
