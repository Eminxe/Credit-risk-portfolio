import numpy as np
import pandas as pd
import yaml

from plata_risk.common import OUTPUTS, ROOT, load_scores, sha256, timestamp, write_json
from plata_risk.economics import break_even_pd, cashflows, load_scenario


def main():
    write_json(OUTPUTS / "case02_manifest.json", {"status": "running"})
    scores, manifest = load_scores()
    s = load_scenario()
    result = scores[["customer_id", "pd_1m", "prediction_type", "LIMIT_BAL"]].copy()
    for key, value in cashflows(scores.pd_1m, scores.LIMIT_BAL, s).items():
        result[key] = value
    result["break_even_pd_1m"] = break_even_pd(scores.LIMIT_BAL, s)
    result["positive_npv_scenario"] = result.npv_twd >= 0
    result.to_parquet(OUTPUTS / "case02_customer_npv.parquet", index=False)
    summary = {"status": "success", "finished_at": timestamp(), "assumptions": s,
               "case01_scores_sha256": manifest["scores_sha256"],
               "scenario_sha256": sha256(ROOT / "configs/scenarios.yaml"),
               "npv_sha256": sha256(OUTPUTS / "case02_customer_npv.parquet"),
               "customers": len(result), "total_npv_twd": float(result.npv_twd.sum()),
               "total_expected_loss_twd": float(result.expected_loss_twd.sum()),
               "positive_npv_customers": int(result.positive_npv_scenario.sum()),
               "interpretation": "Scenario illustration; not Plata profitability or an approval policy"}
    sensitivity = []
    config = yaml.safe_load((ROOT / "configs/scenarios.yaml").read_text())
    for lgd in config["sensitivity"]["lgd"]:
        for rate in config["sensitivity"]["annual_interest_rate"]:
            scenario = {**s, "lgd": lgd, "annual_interest_rate": rate}
            values = cashflows(scores.pd_1m, scores.LIMIT_BAL, scenario)
            sensitivity.append({"lgd": lgd, "annual_interest_rate": rate,
                                "total_npv_twd": float(np.sum(values["npv_twd"]))})
    pd.DataFrame(sensitivity).to_csv(OUTPUTS / "case02_sensitivity.csv", index=False)
    comparisons = []
    for name, overrides in config["comparisons"].items():
        scenario = {**s, **overrides}
        values = cashflows(scores.pd_1m, scores.LIMIT_BAL, scenario)
        comparisons.append({"scenario": name, **overrides,
                            "total_npv_twd": float(np.sum(values["npv_twd"])),
                            "total_expected_loss_twd": float(np.sum(values["expected_loss_twd"]))})
    pd.DataFrame(comparisons).to_csv(OUTPUTS / "case02_horizon_comparison.csv", index=False)
    write_json(OUTPUTS / "case02_manifest.json", summary)
    print(f"Case 02: {len(result)} customers; scenario NPV={summary['total_npv_twd']:,.0f} TWD")


if __name__ == "__main__":
    main()
