"""Independent reconciliation of completed real-data outputs; fail on discrepancies."""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from plata_risk.common import OUTPUTS, ROOT, load_scores, sha256, timestamp, write_json

scores, first = load_scores()
assert len(scores) == 30000
assert set(scores.customer_id) == set(range(1, 30001))
assert scores.observed_default.sum() == 6636
assert scores.pd_1m.notna().all()
hold = scores[scores.prediction_type == "holdout"]
dev = scores[scores.prediction_type == "out_of_fold"]
assert not set(hold.feature_group) & set(dev.feature_group)
metrics = pd.read_csv(OUTPUTS / "case01_model_metrics.csv")
row = metrics[(metrics.split == "holdout") & (metrics.model == first["selected_model"])].iloc[0]
assert np.isclose(row.roc_auc, roc_auc_score(hold.observed_default, hold.pd_1m))
assert np.isclose(row.brier, np.mean((hold.observed_default - hold.pd_1m) ** 2))
deciles = pd.read_csv(OUTPUTS / "case01_risk_deciles.csv")
assert deciles.n.sum() == len(hold)
assert deciles.defaults.sum() == hold.observed_default.sum()
second = json.loads((OUTPUTS / "case02_manifest.json").read_text())
third = json.loads((OUTPUTS / "case03_manifest.json").read_text())
economics = pd.read_parquet(OUTPUTS / "case02_customer_npv.parquet")
limits = pd.read_parquet(OUTPUTS / "case03_limit_strategy.parquet")
for manifest in [second, third]:
    assert manifest["status"] == "success"
    assert manifest["case01_scores_sha256"] == first["scores_sha256"]
    assert manifest["scenario_sha256"] == sha256(ROOT / "configs/scenarios.yaml")
for frame in [economics, limits]:
    assert not frame.customer_id.duplicated().any()
    assert set(frame.customer_id) == set(scores.customer_id)
s = second["assumptions"]
loss = (1 - (1 - economics.pd_1m) ** s["horizon_months"]) * s["lgd"] * economics.LIMIT_BAL * s["utilization"]
np.testing.assert_allclose(loss, economics.expected_loss_twd)
ead = economics.LIMIT_BAL.to_numpy() * s["utilization"]
p = economics.pd_1m.to_numpy()
margin = ead * (s["annual_interest_rate"] - s["annual_funding_rate"]) / 12 - s["monthly_servicing_cost"]
independent_npv = np.full(len(p), -s["acquisition_cost"], dtype=float)
for month in range(1, s["horizon_months"] + 1):
    independent_npv += ((1-p)**month*margin - (1-p)**(month-1)*p*s["lgd"]*ead) / (1+s["annual_discount_rate"])**(month/12)
np.testing.assert_allclose(independent_npv, economics.npv_twd)
assert np.isclose(economics.npv_twd.sum(), second["total_npv_twd"])
assert np.isclose(limits.npv_twd.sum(), third["npv_twd"])
assert limits.expected_loss_twd.sum() <= third["budget_twd"] + 1e-5
assert third["dual_upper_bound_twd"] + 1e-5 >= limits.npv_twd.sum()
assert second["npv_sha256"] == sha256(OUTPUTS / "case02_customer_npv.parquet")
assert third["strategy_sha256"] == sha256(OUTPUTS / "case03_limit_strategy.parquet")
el = pd.read_csv(OUTPUTS / "case02_el_by_decile.csv")
assert el.customers.sum() == len(scores)
assert np.isclose(el.expected_loss_twd.sum(), second["total_expected_loss_twd"])
assert np.isclose(el.npv_twd.sum(), second["total_npv_twd"])
assert el.mean_pd_1m.is_monotonic_increasing
iv = pd.read_csv(OUTPUTS / "case01_information_value.csv")
stability = pd.read_csv(OUTPUTS / "case01_stability.csv")
assert (iv.iv >= 0).all() and iv.feature.is_unique
assert {"score_pd_1m", *iv.feature} == set(stability.variable)
assert (stability.psi >= 0).all()
write_json(OUTPUTS / "verification.json", {
    "status": "passed", "verified_at": timestamp(), "rows": len(scores),
    "checks": ["source IDs and default count", "feature-group split isolation", "holdout AUC and Brier",
               "decile totals", "cross-case customer IDs", "expected loss formula",
               "portfolio sums", "risk budget feasibility", "dual bound", "artifact hashes",
               "EL by decile totals", "IV and PSI coverage"],
})
print("Real-data artifacts verified: 30,000 customers; all reconciliation checks passed")
