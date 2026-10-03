# Project structure and supported entry points

## One working project

The repository root is the working project. The current notebook is
[01_06_casebook.ipynb](notebooks/01_06_casebook.ipynb). Four previous local-only
files were preserved in .tmp/legacy; that directory is ignored and excluded from packaging.
They are not required to clone, run, test or package the project.

## Commands

| Purpose | PowerShell | Linux / WSL |
|---|---|---|
| First setup | .\scripts\run_local.ps1 -Task setup | make setup |
| All six cases | .\scripts\run_local.ps1 -Task pipeline | make pipeline |
| Source/output reconciliation | .\scripts\run_local.ps1 -Task verify | make verify |
| Tests + reconciliation + SQL + notebook | .\scripts\run_local.ps1 -Task validate | make validate |
| Execute notebook and guides | .\scripts\run_local.ps1 -Task notebook | make notebook |
| Start healthy Jupyter | .\scripts\run_local.ps1 -Task jupyter | make jupyter |
| Validated portable archive | .\scripts\run_local.ps1 -Task package | make package |

These commands use Docker. Setup creates .env with the pinned Python container;
it does not depend on a relocated virtual environment or a host scientific Python installation.
Individual case targets case01 through case06 are available in Makefile.
Inside the analytical container, scripts/run_case.sh accepts 01 through 06.

## Contracts

- Cases 01–03 share checked customer IDs and predecessor hashes.
- Cases 04–06 describe separate datasets.
- All PostgreSQL tables are defined in docker/postgres/init.sql. The additional loader
  remains compatible with existing database volumes by creating its own missing tables.
- validate_project.py records the exact source and case-output hashes after checks succeed.
  Source changes during validation stop the run.
- package_portfolio.py refuses missing or stale validation. The portable file boundary
  is defined in src/plata_risk/evidence.py. Raw downloads, local secrets and old scripts
  are outside that boundary.
- Generated reports are outputs; source Markdown and notebook-builder scripts are the
  editable inputs. Change inputs, then validate again to regenerate matching outputs.
- Git tracks selected aggregate evidence and the executed notebook. Raw files, row-level
  scores, serialized models, caches and delivery ZIPs remain ignored.
- Full source-data validation and archive construction run on pushes to main and manual
  GitHub workflow runs. Pull requests run unit/build checks.

Existing CI receipts name the exact tested commit; use the Actions page for the newest run.
