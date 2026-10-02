.PHONY: env build up test case01 case02 case03 pipeline verify sql notebook jupyter down
env:
	python scripts/init_env.py
build:
	docker compose build
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
pipeline:
	docker compose run --rm analytics python scripts/run_pipeline.py
verify:
	docker compose run --rm analytics python scripts/verify_outputs.py
	docker compose run --rm analytics python scripts/verify_additional.py
sql: verify
	docker compose run --rm analytics python scripts/load_postgres.py
	docker compose run --rm analytics python scripts/load_additional_postgres.py
notebook:
	docker compose run --rm analytics python scripts/build_notebook.py
	docker compose run --rm analytics python scripts/execute_notebook.py
jupyter:
	docker compose up -d jupyter
down:
	docker compose down
