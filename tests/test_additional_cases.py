import numpy as np
import pandas as pd
import pytest
from scipy.stats import ttest_ind
from plata_risk.experiment import mean_contrast
from plata_risk.portfolio import roll_rates, summarize_vintages


def test_welch_contrast_matches_independent_scipy():
    a, b = np.array([0, 2, 1, 8, 0, 4]), np.array([0, 0, 1, 0, 3])
    result = mean_contrast(a, b)
    assert result["effect"] == pytest.approx(a.mean()-b.mean())
    assert result["p_value"] == pytest.approx(ttest_ind(a, b, equal_var=False).pvalue)
    assert result["ci_low"] < result["effect"] < result["ci_high"]


def test_contrast_rejects_missing_samples():
    with pytest.raises(ValueError):
        mean_contrast([0, np.nan], [1, 2])


def test_roll_rates_do_not_bridge_missing_months():
    panel = pd.DataFrame({"account_id": [1, 1, 2, 2, 3, 3],
                          "month_end": ["2020-01-31", "2020-03-31", "2020-01-31", "2020-02-29",
                                        "2020-01-31", "2020-02-29"],
                          "state": ["current", "default", "current", "late", "current", "current"]})
    result = roll_rates(panel)
    assert result.transitions.sum() == 2
    assert set(result.next_state) == {"late", "current"}
    np.testing.assert_allclose(result.rate, [.5, .5])
    with pytest.raises(ValueError):
        roll_rates(pd.concat([panel, panel.iloc[[0]]]))


def test_immature_vintage_is_not_reported_as_low_risk():
    frame = pd.DataFrame({"source_row": [1, 2, 3], "issue_month": ["2020-01"]*3,
                          "loan_amnt": [100]*3, "interest_rate": [.1]*3,
                          "loan_status": ["Fully Paid", "Current", "Charged Off"]})
    result = summarize_vintages(frame, ["Fully Paid", "Charged Off"], "Charged Off", .95, 1)
    assert not result.eligible.iloc[0]
    assert np.isnan(result.terminal_chargeoff_rate.iloc[0])

