"""Evaluation diagnostics; never used to select or tune the fitted model."""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss


def grouped_bootstrap(y, p, groups, repetitions=500, seed=42):
    y, p, groups = np.asarray(y), np.asarray(p), np.asarray(groups)
    blocks = [np.flatnonzero(groups == value) for value in np.unique(groups)]
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(repetitions):
        indices = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        if np.unique(y[indices]).size < 2:
            continue
        draws.append([roc_auc_score(y[indices], p[indices]), brier_score_loss(y[indices], p[indices])])
    if len(draws) < repetitions * .9:
        raise ValueError("Too few valid bootstrap draws")
    bounds = np.quantile(draws, [.025, .975], axis=0)
    return pd.DataFrame({"metric": ["roc_auc", "brier"],
                         "estimate": [roc_auc_score(y, p), brier_score_loss(y, p)],
                         "ci_low": bounds[0], "ci_high": bounds[1],
                         "draws": len(draws), "method": "feature-group percentile bootstrap; fixed fitted model"})


def subgroup_diagnostics(frame):
    rows = []
    for feature in ["SEX", "AGE"]:
        bins = (frame[feature].astype(str) if feature == "SEX" else
                pd.cut(frame.AGE, [0, 30, 45, 60, np.inf], right=False).astype(str))
        for group, part in frame.groupby(bins):
            y, p = part.observed_default, part.pd_1m
            rows.append({"feature": feature, "group": group, "n": len(part),
                         "observed_rate": y.mean(), "mean_pd": p.mean(),
                         "brier": brier_score_loss(y, p),
                         "roc_auc": roc_auc_score(y, p) if y.nunique() == 2 else np.nan})
    return pd.DataFrame(rows)

