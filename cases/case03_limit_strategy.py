import json

import numpy as np
import pandas as pd

from plata_risk.common import OUTPUTS, ROOT, load_scores, sha256, timestamp, write_json
from plata_risk.economics import cashflows, limit_pd, load_scenario, optimize_limits


def main():
    write_json(OUTPUTS / "case03_manifest.json", {"status": "running"})
    scores, case01 = load_scores()
    case02 = json.loads((OUTPUTS / "case02_manifest.json").read_text())
    if (case02["status"] != "success" or
        case02["case01_scores_sha256"] != case01["scores_sha256"] or
        case02["scenario_sha256"] != sha256(ROOT / "configs/scenarios.yaml") or
        case02["npv_sha256"] != sha256(OUTPUTS / "case02_customer_npv.parquet")):
        raise ValueError("Case 02 is stale; rerun with the current Case 01 and scenario")
    s = load_scenario()
    multipliers = np.asarray(s["limit_multipliers"])
    baseline_idx = list(multipliers).index(1.0)
    candidate_pd = limit_pd(scores.pd_1m.to_numpy()[:, None], multipliers,
                            s["limit_pd_odds_elasticity"])
    limits = scores.LIMIT_BAL.to_numpy()[:, None] * multipliers
    values = cashflows(candidate_pd, limits, s)
    npv, loss = values["npv_twd"], values["expected_loss_twd"]
    baseline_loss, baseline_npv = loss[:, baseline_idx].sum(), npv[:, baseline_idx].sum()
    # Cross-case reconciliation of the unchanged policy.
    base02 = pd.read_parquet(OUTPUTS / "case02_customer_npv.parquet").set_index("customer_id")
    expected = base02.loc[scores.customer_id, "npv_twd"].to_numpy()
    if not np.allclose(npv[:, baseline_idx], expected, rtol=1e-10, atol=1e-6):
        raise ValueError("Case 02 and Case 03 baseline NPV disagree")
    ids = np.arange(len(scores))
    frontier = []
    selected = None
    ratios = sorted(set(s["frontier_budget_ratios"] + [s["risk_budget_ratio"]]))
    for ratio in ratios:
        budget = float(baseline_loss * ratio)
        try:
            choices, certificate = optimize_limits(npv, loss, budget, baseline_idx)
        except ValueError as exc:
            if "Infeasible budget" not in str(exc):
                raise
            frontier.append({"budget_ratio": ratio, "budget_twd": budget, "feasible": False})
            continue
        row = {"budget_ratio": ratio, "budget_twd": budget, "feasible": True,
               "expected_loss_twd": float(loss[ids, choices].sum()),
               "npv_twd": float(npv[ids, choices].sum()), **certificate}
        if row["expected_loss_twd"] > budget + 1e-5:
            raise ValueError("Optimizer exceeded risk budget")
        frontier.append(row)
        if ratio == s["risk_budget_ratio"]:
            selected = (choices, row)
    if selected is None:
        raise ValueError("Configured risk budget is infeasible")
    choices, summary = selected
    result = pd.DataFrame({"customer_id": scores.customer_id,
                           "baseline_limit_twd": scores.LIMIT_BAL,
                           "limit_multiplier": multipliers[choices],
                           "scenario_limit_twd": limits[ids, choices],
                           "scenario_pd_1m": candidate_pd[ids, choices],
                           "npv_twd": npv[ids, choices], "expected_loss_twd": loss[ids, choices]})
    result.to_parquet(OUTPUTS / "case03_limit_strategy.parquet", index=False)
    frontier = pd.DataFrame(frontier)
    frontier.to_csv(OUTPUTS / "case03_risk_return_frontier.csv", index=False)
    from plata_risk.plots import plt, save
    feasible = frontier[frontier.feasible]
    plt.plot(feasible.expected_loss_twd / 1e6, feasible.npv_twd / 1e6, "o-",
             color="#244b68", label="Feasible scenario strategy")
    if feasible[["expected_loss_twd", "npv_twd"]].drop_duplicates().shape[0] == 1:
        plt.annotate(f"All {len(feasible)} budgets give the same strategy;\nrisk constraint is slack",
                     (feasible.expected_loss_twd.iloc[0] / 1e6, feasible.npv_twd.iloc[0] / 1e6),
                     xytext=(18, -45), textcoords="offset points", fontsize=10)
    plt.scatter([baseline_loss / 1e6], [baseline_npv / 1e6], marker="x", s=80,
                color="#da7a35", label="Unchanged limits")
    plt.xlabel("Scenario expected loss (million TWD)")
    plt.ylabel("Scenario NPV (million TWD)")
    plt.title("UCI 350 | Scenario risk–return comparison")
    plt.legend()
    save("case03_frontier.png")
    write_json(OUTPUTS / "case03_manifest.json", {
        "status": "success", "finished_at": timestamp(), "assumptions": s, **summary,
        "case01_scores_sha256": case01["scores_sha256"],
        "case02_npv_sha256": case02["npv_sha256"], "scenario_sha256": case02["scenario_sha256"],
        "strategy_sha256": sha256(OUTPUTS / "case03_limit_strategy.parquet"),
        "baseline_npv_twd": float(baseline_npv), "baseline_expected_loss_twd": float(baseline_loss),
        "incremental_npv_twd": float(summary["npv_twd"] - baseline_npv),
        "method": "Discrete Lagrangian feasible heuristic with dual gap bound; no exact optimum claim",
        "caveat": "PD response to limits is assumed, not causally estimated; all accounts remain open",
    })
    print(f"Case 03: feasible scenario strategy; dual gap <= {summary['absolute_gap_bound_twd']:,.2f} TWD")


if __name__ == "__main__":
    main()
