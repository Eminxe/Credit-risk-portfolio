from itertools import product

import numpy as np
import pytest

from plata_risk.economics import (
    break_even_pd, cashflows, limit_pd, load_scenario, optimize_limits, validate_scenario,
)


def test_cashflow_one_month_independent_formula():
    s = {**load_scenario(), "horizon_months": 1}
    p, limit = 0.1, 10000.0
    ead = limit * s["utilization"]
    discount = (1 + s["annual_discount_rate"]) ** (1 / 12)
    margin = ead * (s["annual_interest_rate"] - s["annual_funding_rate"]) / 12 - s["monthly_servicing_cost"]
    expected = ((1 - p) * margin - p * s["lgd"] * ead) / discount - s["acquisition_cost"]
    actual = cashflows(p, limit, s)
    assert actual["npv_twd"] == pytest.approx(expected)
    assert actual["expected_loss_twd"] == pytest.approx(p * ead * s["lgd"])


def test_default_probability_boundaries():
    s = load_scenario()
    values = cashflows(np.array([0., 1.]), 10000, s)
    np.testing.assert_allclose(values["pd_horizon"], [0, 1])
    assert values["pv_margin_twd"][1] == 0
    assert values["expected_loss_twd"][0] == 0
    assert values["pv_loss_twd"][1] == pytest.approx(4000 * 0.6 / 1.12 ** (1 / 12))


def test_threshold_and_limit_response():
    s = load_scenario()
    threshold = break_even_pd([200000], s)
    assert cashflows(threshold, [200000], s)["npv_twd"][0] == pytest.approx(0, abs=1e-7)
    np.testing.assert_allclose(limit_pd([0, 0.2, 1], 1, 0.25), [0, 0.2, 1])
    assert limit_pd(0.2, 1.5, 0.25) > 0.2


def test_optimizer_feasibility_and_dual_bound_against_exhaustive_search():
    rng = np.random.default_rng(42)
    for _ in range(15):
        npv = rng.uniform(-10, 20, (4, 3))
        loss = rng.uniform(0, 10, (4, 3))
        budget = float(loss.min(axis=1).sum() + 5)
        choices, certificate = optimize_limits(npv, loss, budget, 1)
        ids = np.arange(4)
        feasible = [sum(npv[i, c] for i, c in enumerate(cs))
                    for cs in product(range(3), repeat=4)
                    if sum(loss[i, c] for i, c in enumerate(cs)) <= budget]
        optimum = max(feasible)
        value = npv[ids, choices].sum()
        assert loss[ids, choices].sum() <= budget + 1e-7
        assert value <= optimum + 1e-7
        assert optimum <= certificate["dual_upper_bound_twd"] + 1e-7
        assert optimum - value <= certificate["absolute_gap_bound_twd"] + 1e-7


def test_infeasible_budget_is_not_silently_relaxed():
    with pytest.raises(ValueError, match="Infeasible"):
        optimize_limits([[2, 3]], [[1, 2]], 0.5, 0)


@pytest.mark.parametrize("key,value", [("lgd", 1.1), ("horizon_months", 1.5),
                                      ("utilization", -1), ("annual_discount_rate", float("nan"))])
def test_bad_assumptions_rejected(key, value):
    with pytest.raises(ValueError):
        validate_scenario({**load_scenario(), key: value})
