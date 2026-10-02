import numpy as np
import pandas as pd
import pytest

from plata_risk.credit import grouped_splits, metrics, risk_deciles
from plata_risk.data import FEATURES, engineer


def test_grouped_holdout_keeps_duplicate_features_together():
    x = pd.DataFrame({"a": np.repeat(np.arange(100), 2)})
    y = np.tile([0, 1], 100)
    groups = pd.util.hash_pandas_object(x, index=False).to_numpy()
    for train, hold in grouped_splits(x, y, groups, n=5):
        assert not set(groups[train]) & set(groups[hold])


def test_metrics_perfect_ranking_and_decile_reconciliation():
    y = np.tile([0, 1], 50)
    p = np.where(y == 1, 0.9, 0.1)
    result = metrics(y, p)
    assert result["roc_auc"] == 1
    assert result["gini"] == 1
    assert result["ks"] == 1
    assert result["brier"] == pytest.approx(0.01)
    deciles = risk_deciles(y, p)
    assert deciles.n.sum() == 100
    assert deciles.defaults.sum() == y.sum()


def test_target_and_id_do_not_enter_feature_engineering():
    df = pd.DataFrame({column: [1., 2.] for column in FEATURES})
    df["customer_id"] = [101, 102]
    df["default"] = [0, 1]
    before = engineer(df)
    df["customer_id"] = [999, 888]
    df["default"] = [1, 0]
    pd.testing.assert_frame_equal(before, engineer(df))
    assert not {"customer_id", "default", "SEX", "MARRIAGE"} & set(before)
