"""Illustrative monthly survival cash flows in historical TWD, not bank estimates."""
import numpy as np
import yaml

from plata_risk.common import ROOT


def load_scenario():
    scenario = yaml.safe_load((ROOT / "configs/scenarios.yaml").read_text())["base"]
    validate_scenario(scenario)
    return scenario


def validate_scenario(s):
    if s["currency"] != "TWD" or s["hazard_assumption"] != "constant_monthly":
        raise ValueError("Unsupported currency or hazard assumption")
    h = s["horizon_months"]
    if isinstance(h, bool) or not isinstance(h, int) or not 1 <= h <= 120:
        raise ValueError("horizon_months must be an integer in [1, 120]")
    for key in ["lgd", "utilization"]:
        if not np.isfinite(s[key]) or not 0 <= s[key] <= 1:
            raise ValueError(key)
    for key in ["annual_interest_rate", "annual_funding_rate", "annual_discount_rate",
                "monthly_servicing_cost", "acquisition_cost", "limit_pd_odds_elasticity",
                "risk_budget_ratio"]:
        if not np.isfinite(s[key]) or s[key] < 0:
            raise ValueError(key)
    for key in ["limit_multipliers", "frontier_budget_ratios"]:
        if not s[key] or any(not np.isfinite(v) or v <= 0 for v in s[key]):
            raise ValueError(key)
    if 1.0 not in s["limit_multipliers"]:
        raise ValueError("Limit grid must contain the unchanged baseline 1.0")


def cashflows(pd_1m, limit, s):
    p, limit = np.broadcast_arrays(np.asarray(pd_1m, float), np.asarray(limit, float))
    if not np.isfinite(p).all() or not np.isfinite(limit).all():
        raise ValueError("Nonfinite economics input")
    if ((p < 0) | (p > 1)).any() or (limit < 0).any():
        raise ValueError("Invalid probability or limit")
    q = 1 - p
    ead = limit * s["utilization"]
    margin = ead * (s["annual_interest_rate"] - s["annual_funding_rate"]) / 12
    margin -= s["monthly_servicing_cost"]
    pv_margin, pv_loss = np.zeros_like(p), np.zeros_like(p)
    for month in range(1, s["horizon_months"] + 1):
        discount = (1 + s["annual_discount_rate"]) ** (month / 12)
        # Margin paid only if surviving month-end; loss paid at first default month-end.
        pv_margin += q ** month * margin / discount
        pv_loss += q ** (month - 1) * p * s["lgd"] * ead / discount
    pd_h = 1 - q ** s["horizon_months"]
    return {"pd_horizon": pd_h, "ead_twd": ead,
            "expected_loss_twd": pd_h * s["lgd"] * ead,
            "pv_loss_twd": pv_loss, "pv_margin_twd": pv_margin,
            "npv_twd": pv_margin - pv_loss - s["acquisition_cost"]}


def limit_pd(p, multiplier, elasticity):
    # Scenario odds multiplier, not an estimated causal limit response.
    p = np.asarray(p, float)
    odds_factor = np.asarray(multiplier, float) ** elasticity
    return p * odds_factor / (1 - p + p * odds_factor)


def break_even_pd(limit, s):
    limit = np.asarray(limit, float)
    lo, hi = np.zeros_like(limit), np.ones_like(limit)
    viable_at_zero = cashflows(lo, limit, s)["npv_twd"] >= 0
    for _ in range(50):
        mid = (lo + hi) / 2
        positive = cashflows(mid, limit, s)["npv_twd"] >= 0
        lo, hi = np.where(positive, mid, lo), np.where(positive, hi, mid)
    return np.where(viable_at_zero, lo, np.nan)


def optimize_limits(npv, loss, budget, baseline_index):
    """Feasible discrete Lagrangian solution with a dual upper bound, not an exact claim."""
    npv, loss = np.asarray(npv, float), np.asarray(loss, float)
    if npv.shape != loss.shape or npv.ndim != 2 or not np.isfinite(npv).all():
        raise ValueError("Invalid candidate matrices")
    if not np.isfinite(loss).all() or (loss < 0).any() or not np.isfinite(budget) or budget < 0:
        raise ValueError("Invalid expected losses or budget")
    ids = np.arange(len(npv))
    minimum = loss.argmin(axis=1)
    if loss[ids, minimum].sum() > budget + 1e-7:
        raise ValueError("Infeasible budget: below minimum expected loss on candidate grid")

    def pick(price):
        choices = (npv - price * loss).argmax(axis=1)
        return choices, float(loss[ids, choices].sum())

    unconstrained, unconstrained_loss = pick(0)
    if unconstrained_loss <= budget:
        value = float(npv[ids, unconstrained].sum())
        return unconstrained, {"shadow_price": 0.0, "dual_upper_bound_twd": value,
                               "absolute_gap_bound_twd": 0.0}
    low, high = 0.0, 1.0
    best = minimum.copy()
    dual = float(npv.max(axis=1).sum())
    while pick(high)[1] > budget:
        high *= 2
        if high > 1e16:
            raise ValueError("Unable to bracket shadow price")
    for _ in range(80):
        price = (low + high) / 2
        choices, total_loss = pick(price)
        upper = (npv - price * loss).max(axis=1).sum() + price * budget
        dual = min(dual, float(upper))
        if total_loss <= budget:
            high = price
            if npv[ids, choices].sum() > npv[ids, best].sum():
                best = choices
        else:
            low = price
    baseline = np.full(len(npv), baseline_index)
    if loss[ids, baseline].sum() <= budget and npv[ids, baseline].sum() > npv[ids, best].sum():
        best = baseline
    value = float(npv[ids, best].sum())
    return best, {"shadow_price": high, "dual_upper_bound_twd": dual,
                  "absolute_gap_bound_twd": max(0.0, dual - value)}
