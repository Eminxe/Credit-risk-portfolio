import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for case in ["case01_credit_default", "case02_product_npv", "case03_limit_strategy",
             "case04_campaign_economics", "case05_causal_hillstrom", "case06_portfolio_vintages"]:
    subprocess.run([sys.executable, str(root / "cases" / f"{case}.py")], cwd=root, check=True)
