"""Classic credit-scorecard diagnostics: Weight of Evidence, Information Value and PSI.

Conventions follow common retail-credit practice:
WoE = ln(share of goods / share of bads); IV = sum((share goods - share bads) * WoE);
PSI = sum((actual share - expected share) * ln(actual share / expected share)).
Empty bins receive additive smoothing so the logarithms stay finite.
"""
import numpy as np
import pandas as pd

SMOOTHING = 0.5


def _is_categorical(values, bins):
    values = pd.Series(values)
    return (not pd.api.types.is_numeric_dtype(values)) or values.nunique() <= bins


def _bin(reference, values, bins):
    """Assign values to bins defined on the reference sample only."""
    reference, values = pd.Series(reference), pd.Series(values)
    if _is_categorical(reference, bins):
        labels = sorted(set(reference.astype(str)) | set(values.astype(str)))
        return pd.Categorical(values.astype(str), categories=labels), labels
    inner = np.unique(np.quantile(reference.to_numpy(float), np.linspace(0, 1, bins + 1))[1:-1])
    codes = np.searchsorted(inner, values.to_numpy(float), side="right")
    edges = np.concatenate([[-np.inf], inner, [np.inf]])
    labels = [f"[{lo:.4g}, {hi:.4g})" for lo, hi in zip(edges[:-1], edges[1:])]
    return pd.Categorical.from_codes(codes, categories=labels), labels


def _shares(counts):
    counts = np.asarray(counts, float)
    return (counts + SMOOTHING) / (counts.sum() + SMOOTHING * len(counts))


def woe_table(feature, target, bins=10):
    """Per-bin Weight of Evidence and IV contribution for a binary target (1 = bad)."""
    target = np.asarray(target)
    if len(target) != len(feature) or not set(np.unique(target)) <= {0, 1}:
        raise ValueError("Target must be binary 0/1 and aligned with the feature")
    binned, labels = _bin(feature, feature, bins)
    frame = pd.DataFrame({"bin": binned, "bad": target})
    table = frame.groupby("bin", observed=False).bad.agg(n="size", bads="sum").reindex(labels)
    table = table.fillna(0)
    table["goods"] = table.n - table.bads
    table["share_goods"] = _shares(table.goods)
    table["share_bads"] = _shares(table.bads)
    table["bad_rate"] = np.where(table.n > 0, table.bads / table.n.where(table.n > 0, 1), np.nan)
    table["woe"] = np.log(table.share_goods / table.share_bads)
    table["iv_contribution"] = (table.share_goods - table.share_bads) * table.woe
    return table.reset_index().rename(columns={"index": "bin"})


def iv_strength(iv):
    """Conventional reading of Information Value (Siddiqi-style thresholds)."""
    if iv < 0.02:
        return "not predictive"
    if iv < 0.1:
        return "weak"
    if iv < 0.3:
        return "medium"
    if iv < 0.5:
        return "strong"
    return "very strong: check for leakage"


def information_values(x, target, bins=10):
    rows, details = [], []
    for column in x:
        table = woe_table(x[column], target, bins)
        iv = float(table.iv_contribution.sum())
        rows.append({"feature": column, "iv": iv, "strength": iv_strength(iv), "bins": len(table)})
        details.append(table.assign(feature=column))
    summary = pd.DataFrame(rows).sort_values("iv", ascending=False).reset_index(drop=True)
    return summary, pd.concat(details, ignore_index=True)


def psi(expected, actual, bins=10):
    """Population Stability Index of `actual` against bins fixed on `expected`."""
    if len(expected) == 0 or len(actual) == 0:
        raise ValueError("PSI requires two nonempty samples")
    expected_bins, labels = _bin(expected, expected, bins)
    actual_bins, _ = _bin(expected, actual, bins)
    e = pd.Series(expected_bins).value_counts().reindex(labels, fill_value=0)
    a = pd.Series(actual_bins).value_counts().reindex(labels, fill_value=0)
    e_share, a_share = _shares(e), _shares(a)
    return float(np.sum((a_share - e_share) * np.log(a_share / e_share)))


def psi_status(value):
    if value < 0.1:
        return "stable"
    if value < 0.25:
        return "moderate shift"
    return "significant shift"


def stability_report(reference, current, columns, bins=10):
    rows = []
    for column in columns:
        value = psi(reference[column], current[column], bins)
        rows.append({"variable": column, "psi": value, "status": psi_status(value)})
    return pd.DataFrame(rows).sort_values("psi", ascending=False).reset_index(drop=True)
