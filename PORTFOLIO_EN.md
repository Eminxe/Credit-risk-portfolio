# Risk analytics: six reproducible public-data studies

**Scope:** independent portfolio research, not a Plata engagement.
**Evidence:** executed Python notebook, PostgreSQL tables, hashed artifacts and independent reconciliation.
**Reading order:** this overview → outputs/casebook.html → code and configuration.

## 01 — Credit default-payment risk

Use 30,000 UCI Taiwan credit-card records to predict next-month default payment.
The source contains 6,636 positive outcomes (22.12%). Features summarize April–September 2005.
Customer ID, outcome, sex and marital status are excluded from predictors.
Identical engineered-feature groups stay together through all splits and calibration.

Compare calibrated logistic regression with histogram gradient boosting. Select by development
out-of-fold log loss before evaluating the reserved 6,006-record holdout.

| Holdout measure | Logistic | Selected boosting |
|---|---:|---:|
| ROC-AUC | 0.752686 | 0.782006 |
| Brier score | 0.140978 | 0.135352 |
| Log loss | 0.447712 | 0.429338 |

The selected AUC has a group-bootstrap 95% interval of **0.7669–0.7965** (500 draws;
conditional on the fitted model). Subgroup diagnostics are included, without a fairness certification.
This is grouped random validation on historical data. It cannot establish future-period or Plata performance.

## 02 — Risk-to-NPV scenario engine

Link the scored customer artifact to monthly survival cash flows, explicit utilization and LGD,
and annual discounting. Preserve OOF scores for development customers and held-out predictions
for reserved customers. This is a research portfolio, not a single production scoring deployment.

The original 12-month scenario uses 24% annual interest, 8% funding, 12% discounting,
40% utilization, 60% LGD, monthly servicing of 30 TWD and acquisition cost of 500 TWD.
Its NPV is **−723.84 million TWD**. A one-month existing-account comparison with zero acquisition
cost gives **−185.77 million TWD**. Neither value is observed profit or an investment forecast.
One-month default payment is not validated as a constant multi-month loss hazard.

## 03 — Limit strategy under a scenario loss budget

Search multipliers 0.75, 1, 1.25 and 1.5 using an assumed PD-odds elasticity of 0.25.
Return a feasible discrete allocation with a dual upper bound on its objective.
Under the original assumptions, every account selects 0.75: NPV becomes **−528.62 million TWD**,
a **195.21 million TWD scenario improvement** while remaining negative.
The five configured budgets produce the same allocation: the risk constraint is slack.
There is no demonstrated nontrivial frontier or causal justification for cutting every limit.

## 04 — Campaign response: an honest drift finding

Use 45,211 UCI Bank Marketing records in documented source date order.
Exclude call duration and current-campaign contact fields. Use a 60%/20%/20% ordered
training/validation/holdout design and expanding-window calibration.

The selected model's later-holdout AUC is **0.5923**, Brier **0.2689** and log loss **0.8399**.
A development-prevalence baseline has log loss **0.8994**. These results show limited ranking
and substantial probability error; they do not justify deployment.
EUR response-value/contact-cost assumptions give retrospective proxies, not incremental campaign ROI.
No no-contact control is available in this source.

## 05 — Randomized email incrementality

Use all 64,000 Hillstrom customers assigned to men's email, women's email or no email.
Estimate two-week intent-to-treat effects against control, Welch pointwise 95% intervals,
and Holm-adjusted p-values across six contrasts.

Men's email raises conversion by **0.6805 percentage points** and spend by **$0.7698/customer**;
women's email raises conversion by **0.3111 points** and spend by **$0.4244/customer**.
At an assumed 40% contribution margin and $0.05 email cost, net contribution differences are
**$0.2579** and **$0.1198** per assigned customer. Source randomization supports causal
interpretation for this retailer and window; transfer to another business requires new evidence.

## 06 — Vintage monitoring with clear endpoint definitions

Load the original LendingClub archive: 42,535 loan records after removing three footer rows.
Exclude 2,749 explicitly non-policy loans. Among the remaining **39,786 loans**, **5,670**
are charged off: **14.2512%** of terminal outcomes. Of 55 monthly origination cohorts,
42 meet the reporting rule of at least 100 loans and 95% terminal coverage.

Grade and vintage charts describe final status at an undated snapshot. They are not fixed-horizon
PD estimates or monthly delinquency transitions. The repository provides a tested roll-rate
function for future account-month data; it does not invent missing historical transitions.

## Engineering and review evidence

Python 3.12, Docker Compose, PostgreSQL 16, executed Jupyter notebook, 16 passing unit tests,
independent source reconciliation and idempotent SQL loads. The pipeline preserves data receipts,
SHA-256 lineage and explicit assumptions. Image digests and Python package versions are pinned.
Full remote CI passed on 2026-10-02 (GitHub Actions run 37004011370); all six studies and infrastructure checks succeeded.

This project was developed with AI coding assistance. The inspectable calculations and limitations,
rather than unverified claims of business impact, are the portfolio evidence.

## Sources

- Yeh, I. (2009), [Default of Credit Card Clients](https://doi.org/10.24432/C55S3H), UCI, CC BY 4.0.
- Moro, Cortez and Rita, [Bank Marketing](https://doi.org/10.24432/C5K306), UCI, CC BY 4.0.
- Kevin Hillstrom, [MineThatData challenge](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html).
- [Original LendingClub LoanStats3a archive](https://resources.lendingclub.com/LoanStats3a.csv.zip);
  the download receipt records the upstream redirect and hash.

Exact outputs and uncertainty tables: [executed casebook](outputs/casebook.html).

