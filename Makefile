.PHONY: setup env build up test case01 case02 case03 case04 case05 case06 pipeline verify validate sql notebook package jupyter down
setup:
	bash scripts/bootstrap.sh
env:
	python scripts/init_env.py
build:
	docker compose build analytics
up:
	docker compose up -d --wait postgres
test:
	docker compose run --rm analytics bash scripts/test.sh
case01:
	docker compose run --rm analytics python cases/case01_credit_default.py
case02:
	docker compose run --rm analytics python cases/case02_product_npv.py
case03:
	docker compose run --rm analytics python cases/case03_limit_strategy.py
case04:
	docker compose run --rm analytics python cases/case04_campaign_economics.py
case05:
	docker compose run --rm analytics python cases/case05_causal_hillstrom.py
case06:
	docker compose run --rm analytics python cases/case06_portfolio_vintages.py
pipeline:
	docker compose run --rm analytics python scripts/run_pipeline.py
verify:
	docker compose run --rm analytics python scripts/verify_outputs.py
	docker compose run --rm analytics python scripts/verify_additional.py
sql: verify
	docker compose run --rm analytics python scripts/load_postgres.py
	docker compose run --rm analytics python scripts/load_additional_postgres.py
validate:
	docker compose run --rm analytics python scripts/validate_project.py
package:
	docker compose run --rm analytics python scripts/package_portfolio.py
notebook:
	docker compose run --rm analytics python scripts/build_notebook.py
	docker compose run --rm analytics python scripts/execute_notebook.py
	docker compose run --rm analytics python scripts/export_reading_guides.py
jupyter:
	docker compose up -d --wait jupyter
down:
	docker compose down
