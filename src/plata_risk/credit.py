import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, brier_score_loss, log_loss, precision_recall_curve,
    roc_auc_score, roc_curve, auc,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42


def grouped_splits(x, y, groups, n=3):
    return list(StratifiedGroupKFold(n_splits=n, shuffle=True, random_state=SEED)
                .split(x, y, groups))


def calibrated_model(name, x, y, groups):
    categorical = ["EDUCATION"]
    numeric = [c for c in x if c not in categorical]
    transform = ColumnTransformer([
        ("numeric", StandardScaler(), numeric),
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
    ])
    if name == "logistic":
        estimator = LogisticRegression(C=1.0, max_iter=3000, random_state=SEED)
    elif name == "hist_gradient_boosting":
        estimator = HistGradientBoostingClassifier(
            max_iter=120, max_leaf_nodes=15, learning_rate=0.06,
            l2_regularization=5.0, early_stopping=False, random_state=SEED,
        )
    else:
        raise ValueError(name)
    # Calibration folds respect feature-duplicate groups, as do outer folds.
    return CalibratedClassifierCV(make_pipeline(transform, estimator), method="sigmoid",
                                  cv=grouped_splits(x, y, groups), n_jobs=1)


def metrics(y, p):
    fpr, tpr, _ = roc_curve(y, p)
    precision, recall, _ = precision_recall_curve(y, p)
    area = roc_auc_score(y, p)
    return {"roc_auc": float(area), "gini": float(2 * area - 1),
            "ks": float(np.max(tpr - fpr)),
            "average_precision": float(average_precision_score(y, p)),
            "pr_auc_trapezoid": float(auc(recall, precision)),
            "brier": float(brier_score_loss(y, p)), "log_loss": float(log_loss(y, p)),
            "n": len(y), "default_rate": float(np.mean(y))}


def risk_deciles(y, p):
    frame = pd.DataFrame({"observed": np.asarray(y), "pd_1m": p})
    # Stable rank tie-breaking keeps ten equal-count reporting bins.
    frame["decile"] = pd.qcut(frame.pd_1m.rank(method="first"), 10, labels=False) + 1
    result = frame.groupby("decile").agg(
        n=("observed", "size"), defaults=("observed", "sum"),
        observed_rate=("observed", "mean"), mean_pd=("pd_1m", "mean"))
    return result.reset_index()
