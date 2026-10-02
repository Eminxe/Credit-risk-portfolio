"""Build an executable, source-backed companion from successful case artifacts."""
import json
from pathlib import Path

import nbformat as nbf
import pandas as pd

from plata_risk.common import OUTPUTS, load_scores

scores, first = load_scores()
metrics = pd.read_csv(OUTPUTS / "case01_model_metrics.csv")
row = metrics[(metrics.model == first["selected_model"]) & (metrics.split == "holdout")].iloc[0]
second = json.loads((OUTPUTS / "case02_manifest.json").read_text())
third = json.loads((OUTPUTS / "case03_manifest.json").read_text())
if second["status"] != "success" or third["status"] != "success":
    raise SystemExit("Run Cases 01-03 before building the notebook")
limits = pd.read_parquet(OUTPUTS / "case03_limit_strategy.parquet")
frontier = pd.read_csv(OUTPUTS / "case03_risk_return_frontier.csv")
counts = "; ".join(f"{int(n):,} accounts at {m:g}×" for m, n in limits.limit_multiplier.value_counts().items())
flat = frontier.loc[frontier.feasible, ["expected_loss_twd", "npv_twd"]].drop_duplicates().shape[0] == 1
frontier_note = ("All configured feasible budgets give the same point; the data do not demonstrate "
                 "a nontrivial risk-budget trade-off under these assumptions." if flat else
                 "The frontier reports feasible scenario solutions for the declared risk budgets.")
nb = nbf.v4.new_notebook()
nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
    md("# Plata Risk Casebook — Six public-data studies\n\n## Executive overview\n\n"
       f"Real UCI data: **{len(scores):,} clients**. The selected model is **{first['selected_model']}**, "
       f"chosen by development out-of-fold log loss. On the untouched grouped holdout "
       f"(**{int(row['n']):,} clients**), ROC-AUC is **{row.roc_auc:.4f}**, "
       f"Gini **{row.gini:.4f}**, KS **{row.ks:.4f}**, Brier **{row.brier:.4f}**.\n\n"
       "These are historical Taiwan default-payment results, not validation on Plata customers.\n\n"
       f"Under the explicit base scenario, total NPV is **{second['total_npv_twd']:,.0f} TWD**. "
       f"The feasible limit strategy changes it by **{third['incremental_npv_twd']:,.0f} TWD**. "
       "These monetary values are hypothetical scenario outputs, not observed profit."),
    md("## Context & Methods\n\n"
       "A behavioral score uses information available through September 2005 to predict next-month "
       "default payment. No customer ID or outcome enters predictors. Sex and marital status are "
       "excluded; this does not establish fairness or legal suitability. Identical engineered-feature "
       "groups stay together through holdout, outer CV and inner calibration. Sigmoid calibration "
       "is fitted within training partitions. A grouped random split is not temporal validation.\n\n"
       "### Key Assumptions\n\n"
       "Economics uses TWD, constant monthly conditional hazard, fixed utilization and LGD; margins "
       "stop at default and losses occur at first default month-end. Annual compounding discounts "
       "monthly cash flows. This extrapolation of one-month default-payment scores is unvalidated. "
       "Limit response is an assumed odds elasticity, not causal evidence. All accounts remain open "
       "on the candidate grid. The optimizer returns a feasible solution with a dual gap bound, "
       "not an unqualified exact optimum."),
    code("import json\nimport pandas as pd\n"
         "from IPython.display import display, Image\n"
         "from plata_risk.common import OUTPUTS, load_scores\n"
         "scores, manifest = load_scores()\n"
         "display(pd.Series(json.loads((OUTPUTS / 'case02_manifest.json').read_text())['assumptions'], name='Scenario assumptions'))"),
    md("## Data\n\n"
       "Source: I-Cheng Yeh, UCI Default of Credit Card Clients, "
       "[DOI 10.24432/C55S3H](https://doi.org/10.24432/C55S3H), CC BY 4.0. "
       "Raw archive and download SHA-256 are cached in `data/raw`. No synthetic data is used. "
       "Repayment codes absent from the source dictionary are retained as codes; negative bill "
       "balances are preserved. Education codes outside 1–4 are grouped as unknown."),
    code("display(pd.Series(json.loads((OUTPUTS / 'case01_data_audit.json').read_text()), name='Data audit'))\n"
         "display(scores[['customer_id', 'LIMIT_BAL', 'pd_1m', 'prediction_type']].head())"),
    md("## Results\n\n### Credit risk discrimination and calibration\n\n"
       "Only holdout results estimate out-of-sample performance after model selection. Development "
       "OOF metrics were used for selection and are not independent final estimates. Average "
       "precision and trapezoidal PR-AUC are reported separately."),
    code("display(pd.read_csv(OUTPUTS / 'case01_model_metrics.csv').round(5))\n"
         "display(Image(filename=str(OUTPUTS / 'case01_roc.png')))\n"
         "display(Image(filename=str(OUTPUTS / 'case01_calibration.png')))"),
    md("### Risk deciles\n\nDecile 10 contains the highest predicted risk. Stable rank tie-breaking "
       "creates ten near-equal-count bins; observed default rates remain holdout-only."),
    code("display(pd.read_csv(OUTPUTS / 'case01_risk_deciles.csv').round(4))\n"
         "display(Image(filename=str(OUTPUTS / 'case01_default_by_decile.png')))"),
    md("### Scenario economics and limit strategy\n\n"
       "The monetary sensitivity table varies assumptions; it is not a confidence interval. "
       "A negative NPV is retained as a finding under the assumptions, without changing rates "
       f"to manufacture profitability. Chosen multipliers: {counts}. {frontier_note}"),
    code("display(pd.read_csv(OUTPUTS / 'case02_sensitivity.csv').round(2))\n"
         "display(pd.read_csv(OUTPUTS / 'case03_risk_return_frontier.csv').round(2))\n"
         "display(Image(filename=str(OUTPUTS / 'case03_frontier.png')))"),
    md("## Takeaways\n\n"
       "The three cases share verified customer IDs and hashed artifacts. Economics consumes "
       "out-of-fold predictions for development customers and holdout predictions for the reserved "
       "customers. Prediction models differ across folds, so portfolio scores are research estimates, "
       "not a deployed single-model portfolio.\n\n"
       "Before real decisions: obtain current representative data, validate over time, evaluate "
       "fairness, estimate actual costs and recovery timing, and identify a causal limit-response "
       "model. No production credit decisions are justified by these historical experiments."),
]
nb.cells.extend([
    md("## Evaluation uncertainty and subgroup diagnostics\n\n"
       "The 95% intervals resample identical-feature groups in the holdout with the fitted model fixed "
       "(500 draws). They do not capture retraining uncertainty or future population drift. "
       "Subgroup metrics describe this sample; they are not a fairness certification."),
    code("display(pd.read_csv(OUTPUTS / 'case01_uncertainty.csv'))\n"
         "display(pd.read_csv(OUTPUTS / 'case01_subgroups.csv'))\n"
         "display(pd.read_csv(OUTPUTS / 'case02_horizon_comparison.csv'))"),
    md("## Case 04 — Campaign response and scenario economics\n\n"
       "[UCI Bank Marketing](https://doi.org/10.24432/C5K306), 45,211 records. "
       "The final 20% in source date order is held out. Model selection uses the preceding 20%; "
       "calibration uses expanding windows with matching-feature groups removed from training. "
       "Duration and current-campaign fields are excluded. Customer IDs and exact dates are unavailable. "
       "The selected model shows weak ranking and substantial probability drift on the later holdout. "
       "This is a limitation to investigate, not a deployment recommendation. Historical response "
       "among contacted customers cannot identify incremental campaign uplift. EUR economics is illustrative."),
    code("display(pd.read_csv(OUTPUTS / 'case04_metrics.csv'))\n"
         "display(pd.read_csv(OUTPUTS / 'case04_policies.csv'))\n"
         "display(Image(filename=str(OUTPUTS / 'case04_policy_response.png')))"),
    md("## Case 05 — Randomized email experiment\n\n"
       "[Hillstrom research challenge](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html), "
       "64,000 customers assigned to two email arms or no email. Intent-to-treat outcomes cover two weeks. "
       "Welch intervals are pointwise; Holm p-values adjust six comparisons. "
       "Contribution margin and email cost are explicit USD scenario assumptions. "
       "Baseline balance supports diagnostics but does not prove assignment integrity."),
    code("display(pd.read_csv(OUTPUTS / 'case05_arm_summary.csv'))\n"
         "display(pd.read_csv(OUTPUTS / 'case05_ate.csv'))\n"
         "display(pd.read_csv(OUTPUTS / 'case05_email_economics.csv'))\n"
         "display(Image(filename=str(OUTPUTS / 'case05_conversion_effect.png')))\n"
         "display(Image(filename=str(OUTPUTS / 'case05_spend_effect.png')))"),
    md("## Case 06 — Vintage monitoring with terminal outcomes\n\n"
       "[Original LendingClub archive](https://resources.lendingclub.com/LoanStats3a.csv.zip), "
       "2007–2011 originations. Exclude the explicitly identified non-policy loans. "
       "Only cohorts with at least 100 loans and 95% terminal coverage receive a reported rate. "
       "This undated snapshot supports terminal charge-off proportions; it does not support "
       "fixed-horizon default probabilities or observed month-to-month roll rates. "
       "A separate tested roll-rate function is provided for a future true loan-month panel."),
    code("display(pd.Series(json.loads((OUTPUTS / 'case06_manifest.json').read_text())))\n"
         "display(pd.read_csv(OUTPUTS / 'case06_grade_summary.csv'))\n"
         "display(Image(filename=str(OUTPUTS / 'case06_vintages.png')))\n"
         "display(Image(filename=str(OUTPUTS / 'case06_grades.png')))"),
    md("## Reproduction and evidence\n\n"
       "Run Docker Compose with Python 3.12 and PostgreSQL 16. The pipeline, independent source "
       "reconciliation, transactional SQL loaders and this executable notebook form the evidence trail. "
       "Cases 01–03 share customer IDs and predecessor hashes. Cases 04–06 are distinct populations "
       "and are not joined to UCI credit clients. Sources and code are cited in the repository; "
       "no private Plata data, bank pricing or measured bank profit is claimed.")
])
nbf.validate(nb)
path = Path(__file__).resolve().parents[1] / "notebooks" / "01_06_casebook.ipynb"
path.parent.mkdir(exist_ok=True)
nbf.write(nb, path)
print(path)
