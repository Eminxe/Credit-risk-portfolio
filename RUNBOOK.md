# Continuation runbook

1. Read README.md, EXECUTION_STATUS.md and CI_RESULT.md. This is a reconstruction.
2. Inspect `git status` and preserve existing user changes. Do not alter synced parent `sources/`.
3. Obtain a functioning Docker Desktop Linux engine/WSL2 session if unavailable. Do not
   misinterpret installed CLI binaries as a running engine. Avoid reinstalling registered Ubuntu.
4. Run `bash scripts/bootstrap.sh`, or `.\scripts\run_local.ps1 -Task setup` in PowerShell.
   Both generate .env using the pinned Python container and preserve existing secrets.
5. Run `docker compose config --quiet`, build, start PostgreSQL with `--wait`, run tests.
6. Run the real-data pipeline for all six cases. Never substitute synthetic outputs.
7. Run `scripts/validate_project.py` in analytics: independent reconciliation, SQL load/idempotence,
   all three 30,000-row tables and 138 aggregate records for the current three additional case versions.
   Historical versions are retained, so the aggregate table may contain more rows.
8. The current notebook is `notebooks/01_06_casebook.ipynb`; execute it and inspect the figures.
   Run `docker compose up -d --wait jupyter`, then `docker compose exec -T jupyter python scripts/healthcheck.py`.
   Employer reading guide: PORTFOLIO_EN.md; owner explanation: РАЗБОР_RU.md.
9. Record actual check results. Do not claim local Docker, SQL, CI or notebook execution if blocked.

The latest verified data receipt resides in `data/raw/uci350_source.json`. Selected aggregate
evidence and reports are tracked; raw files, individual scores and model binaries stay ignored.
`case01_manifest.json` chooses the model before holdout evaluation.
Economic assumptions are scenarios in TWD. Preserve these limitations in any portfolio write-up.

For VS Code, open this repository and choose Dev Containers: Reopen in Container.
The devcontainer uses the same Python 3.12 analytical image. Ubuntu's system Python is separate.
Recommended extensions are listed in `.vscode/extensions.json`.
No API key is required for the analytical pipeline.

Packaging: run scripts/validate_project.py, then scripts/package_portfolio.py.
Packaging rejects a receipt if any included project source or case output changed after validation.
Keep legacy local material in .tmp/legacy; it is not part of the deliverable.
