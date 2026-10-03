#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-}" in
  01) python cases/case01_credit_default.py ;;
  02) python cases/case02_product_npv.py ;;
  03) python cases/case03_limit_strategy.py ;;
  04) python cases/case04_campaign_economics.py ;;
  05) python cases/case05_causal_hillstrom.py ;;
  06) python cases/case06_portfolio_vintages.py ;;
  *) echo 'Usage: bash scripts/run_case.sh {01|02|03|04|05|06}' >&2; exit 2 ;;
esac
