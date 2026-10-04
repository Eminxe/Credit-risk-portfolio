import numpy as np
import pandas as pd
import pytest

from plata_risk.scorecard import information_values, iv_strength, psi, psi_status, woe_table


def test_woe_matches_hand_calculation():
    # Two categories: A has 80 goods / 20 bads, B has 20 goods / 80 bads.
    feature = ["A"] * 100 + ["B"] * 100
    target = [0] * 80 + [1] * 20 + [0] * 20 + [1] * 80
    table = woe_table(feature, target).set_index("bin")
    share_goods = (np.array([80, 20]) + .5) / 101
    share_bads = (np.array([20, 80]) + .5) / 101
    woe = np.log(share_goods / share_bads)
    np.testing.assert_allclose(table.woe, woe)
    assert table.loc["A", "woe"] > 0 > table.loc["B", "woe"]
    assert table.iv_contribution.sum() == pytest.approx(np.sum((share_goods - share_bads) * woe))
    assert table.loc["A", "bad_rate"] == pytest.approx(.2)


def test_information_value_ranks_signal_above_noise():
    rng = np.random.default_rng(0)
    signal = rng.normal(size=5000)
    target = (rng.random(5000) < 1 / (1 + np.exp(-2 * signal))).astype(int)
    x = pd.DataFrame({"signal": signal, "noise": rng.normal(size=5000)})
    summary, details = information_values(x, target)
    assert list(summary.feature) == ["signal", "noise"]
    assert summary.iv.iloc[0] > .5 and summary.iv.iloc[1] < .02
    assert set(details.feature) == {"signal", "noise"}


def test_psi_zero_for_identical_and_large_for_shifted():
    rng = np.random.default_rng(1)
    base = rng.normal(size=10000)
    assert psi(base, base) == pytest.approx(0, abs=1e-12)
    assert psi_status(psi(base, rng.normal(size=10000))) == "stable"
    assert psi_status(psi(base, rng.normal(1.0, 1, size=10000))) == "significant shift"


def test_psi_handles_categories_missing_from_reference():
    assert psi(["a"] * 50 + ["b"] * 50, ["a"] * 50 + ["c"] * 50) > .25


def test_iv_strength_thresholds():
    assert [iv_strength(v) for v in [.01, .05, .2, .4, .8]] == [
        "not predictive", "weak", "medium", "strong", "very strong: check for leakage"]


def test_woe_rejects_nonbinary_target():
    with pytest.raises(ValueError):
        woe_table([1, 2, 3], [0, 1, 2])
