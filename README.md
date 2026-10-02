# Credit-risk-portfolio

Credit risk analytics portfolio by Emin Salavatov. Independent case studies for a Risk Analyst application at Banco Plata.


Six reproducible public-data studies for a risk/data analytics portfolio. This independent
research project uses no private Plata data and claims no production deployment or measured bank profit.

Start with [Portfolio overview](PORTFOLIO_EN.md), the executed
[English notebook](notebooks/01_06_casebook.ipynb), or the self-contained
[HTML casebook](outputs/casebook.html). Russian explanation: [РАЗБОР_RU.md](РАЗБОР_RU.md).

| Case | Question | Evidence |
|---|---|---|
| 01 | Predict next-month default payment | UCI, 30,000 clients; grouped nested calibration and holdout |
| 02 | Translate risk into cash-flow scenarios | Explicit TWD assumptions; independent formula reconciliation |
| 03 | Choose limits under a loss budget | Discrete candidate grid; feasible solution and dual bound |
| 04 | Rank campaign response | UCI Bank Marketing; ordered validation/holdout; drift limitation |
| 05 | Estimate incremental email effects | Hillstrom randomized no-email control; uncertainty and Holm correction |
| 06 | Monitor vintage outcomes | Original LendingClub snapshot; terminal outcomes, not roll rates |

## Verified on GitHub

[Full validation run](https://github.com/Eminxe/Credit-risk-portfolio/actions/runs/37004011370) passed on 2026-10-02: all six studies,
16 tests, independent reconciliation, PostgreSQL, executed notebook and authenticated Jupyter.
See [CI evidence](CI_RESULT.md) for the tested commit and downloadable results.

## Reproduce

Docker Desktop with Linux containers is required. Run from this repository in PowerShell
or a Linux terminal. Python 3.12 runs inside the container; the Ubuntu system interpreter
does not need to be replaced.

```text
python scripts/init_env.py
docker compose build analytics
docker compose up -d --wait postgres
docker compose run --rm analytics python scripts/run_pipeline.py
docker compose run --rm analytics python scripts/validate_project.py
docker compose up -d jupyter
```

Open http://localhost:8888 and use the locally generated JUPYTER_TOKEN from .env.
PostgreSQL is bound to localhost:5433. Never include .env in a portfolio archive.
The project has digest-pinned base images and a tested requirements-linux.lock.
VS Code: open this folder and choose **Dev Containers: Reopen in Container** to use
the same Python 3.12 environment. The Dev Containers configuration is included.
First execution downloads public sources; caches are validated against stored SHA-256 receipts.
Upstream availability is required when caches are absent.

The pipeline fails instead of substituting generated data. Validation checks model metrics,
source labels, cross-case IDs, economics, experimental contrasts, vintage aggregation, SQL
row counts/idempotence and notebook execution. Unit fixtures are never analysis inputs.

## Layout

- cases/: six executable studies.
- src/plata_risk/: data access, transforms, scoring, economics, statistics and plotting.
- configs/: explicit financial and analytical assumptions.
- scripts/: orchestration, validation, SQL loaders, notebook export and packaging.
- docker/postgres/init.sql: core relational schema; additional aggregate tables are created
  idempotently by scripts/load_additional_postgres.py.
- outputs/: locally generated evidence, manifests, model artifacts and HTML.
- tests/: methodological edge cases and independent formula checks.
- RUNBOOK.md: continuation instructions; EXECUTION_STATUS.md: actual execution status.

Cases 01–03 share UCI credit IDs and hashed predecessor files. Cases 04–06 are independent
populations, never joined to those IDs. Joblib artifacts are executable Python serialization:
load only this project's trusted local models.

## Sources and limitations

[UCI credit](https://doi.org/10.24432/C55S3H) and
[UCI marketing](https://doi.org/10.24432/C5K306) are CC BY 4.0;
[Hillstrom](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html)
and [LendingClub archive](https://resources.lendingclub.com/LoanStats3a.csv.zip)
have source receipts but no established redistribution license in this project.
The deliverable excludes raw datasets. Historical UCI scores are not regulatory default
probabilities; scenario LGD, prices and limit response are not measured bank parameters.

CI configuration is included. See the repository Actions tab for remote run results.
Local execution does not count as a remote CI pass. The original unavailable ZIP was reconstructed, not recovered.

