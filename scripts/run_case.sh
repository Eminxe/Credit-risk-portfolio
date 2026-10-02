#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-}" in
  01) python cases/case01_credit_default.py ;;
  02) python cases/case02_product_npv.py ;;
  03) python cases/case03_limit_strategy.py ;;
  *) echo 'Usage: bash scripts/run_case.sh {01|02|03}' >&2; exit 2 ;;
esac
