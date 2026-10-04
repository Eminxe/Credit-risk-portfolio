"""Independent source-to-output checks for Cases 04–06."""
import json
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
from sklearn.metrics import roc_auc_score, log_loss
from plata_risk.common import OUTPUTS, ROOT, sha256, timestamp, write_json
from plata_risk.sources import load_bank, load_hillstrom, load_lendingclub

bank, _ = load_bank()
scores = pd.read_csv(OUTPUTS / "case04_holdout_scores.csv")
source = bank.iloc[scores.source_row.to_numpy()-1]
np.testing.assert_array_equal(source.y.eq("yes").astype(int), scores.observed_subscription)
assert len(scores) == len(bank)-int(.8*len(bank))
assert scores.p_subscription.between(0, 1).all() and scores.source_row.is_unique
manifest = json.loads((OUTPUTS / "case04_manifest.json").read_text())
groups = pd.util.hash_pandas_object(bank.drop(columns=manifest["excluded_predictors"]), index=False)
cut1, cut2 = int(.6*len(bank)), int(.8*len(bank))
hold_groups = set(groups.iloc[cut2:])
valid_indices = [i for i in range(cut1, cut2) if groups[i] not in hold_groups]
valid_groups = set(groups.iloc[valid_indices])
train_indices = [i for i in range(cut1) if groups[i] not in valid_groups | hold_groups]
assert not set(groups.iloc[train_indices]) & (valid_groups | hold_groups)
assert len(valid_indices) == manifest["validation_rows"]
assert len(train_indices) == manifest["selection_training_rows"]
metrics = pd.read_csv(OUTPUTS / "case04_metrics.csv")
row = metrics[(metrics.model == manifest["selected_model"]) & (metrics.split == "ordered_holdout")].iloc[0]
assert np.isclose(row.roc_auc, roc_auc_score(scores.observed_subscription, scores.p_subscription))
assert np.isclose(row.log_loss, log_loss(scores.observed_subscription, scores.p_subscription))
ranked = scores.sort_values(["p_subscription", "source_row"], ascending=[False, True])
for row in pd.read_csv(OUTPUTS / "case04_policies.csv").itertuples():
    part = ranked.head(row.contacts)
    assert row.observed_subscriptions == part.observed_subscription.sum()
    s = manifest["assumptions"]
    assert np.isclose(row.retrospective_net_proxy_eur,
                      part.observed_subscription.sum()*s["value_per_subscription"]-len(part)*s["cost_per_contact"])

stability = pd.read_csv(OUTPUTS / "case04_stability.csv")
assert set(stability.variable) == {"score", *bank.drop(columns=manifest["excluded_predictors"]).columns}
assert (stability.psi >= 0).all()
assert np.isclose(stability.loc[stability.variable == "score", "psi"].iloc[0], manifest["score_psi"])

hill, _ = load_hillstrom()
control = hill[hill.segment == "No E-Mail"]
effects = pd.read_csv(OUTPUTS / "case05_ate.csv")
raw_p = []
for row in effects.itertuples():
    arm = hill[hill.segment == row.arm]
    assert row.n_treatment == len(arm) and row.n_control == len(control)
    assert np.isclose(row.effect, arm[row.outcome].mean()-control[row.outcome].mean())
    raw_p.append(ttest_ind(arm[row.outcome], control[row.outcome], equal_var=False).pvalue)
np.testing.assert_allclose(effects.p_value, raw_p, rtol=1e-8)
order = np.argsort(raw_p)
adjusted = np.empty(len(raw_p))
adjusted[order] = np.minimum(1, np.maximum.accumulate(np.asarray(raw_p)[order]*np.arange(len(raw_p), 0, -1)))
np.testing.assert_allclose(effects.p_holm, adjusted, rtol=1e-8)

loans, _ = load_lendingclub()
eligible = loans[~loans.loan_status.str.startswith("Does not meet the credit policy")]
vintages = pd.read_csv(OUTPUTS / "case06_vintages.csv")
assert vintages.n.sum() == len(eligible)
assert vintages.bad_n.sum() == eligible.loan_status.eq("Charged Off").sum()
assert np.isclose(vintages.originated_usd.sum(), eligible.loan_amnt.sum())
np.testing.assert_allclose(vintages.loc[vintages.eligible, "terminal_chargeoff_rate"],
                           (vintages.bad_n/vintages.terminal_n)[vintages.eligible])
assert vintages.loc[~vintages.eligible, "terminal_chargeoff_rate"].isna().all()

files = {"case04": "case04_holdout_scores.csv", "case05": "case05_ate.csv", "case06": "case06_vintages.csv"}
for case, filename in files.items():
    m = json.loads((OUTPUTS / f"{case}_manifest.json").read_text())
    assert m["status"] == "success" and m["results_sha256"] == sha256(OUTPUTS / filename)
write_json(OUTPUTS / "verification_additional.json", {
    "status": "passed", "verified_at": timestamp(),
    "configuration_sha256": sha256(ROOT / "configs/additional_cases.yaml"),
    "checks": ["bank source-row labels and holdout metrics", "campaign scenario arithmetic",
               "Hillstrom arm denominators and raw mean effects", "independent Welch tests and Holm correction",
               "LendingClub eligibility, cohort counts, losses and principal", "artifact hashes"]})
print("Cases 04–06 independently reconciled with source records")

