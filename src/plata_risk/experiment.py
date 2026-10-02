"""Randomized intent-to-treat contrasts, uncertainty and multiplicity."""
import numpy as np
from scipy import stats


def mean_contrast(treatment, control, alpha=0.05):
    treatment, control = np.asarray(treatment, float), np.asarray(control, float)
    if min(len(treatment), len(control)) < 2 or not np.isfinite(treatment).all() or not np.isfinite(control).all():
        raise ValueError("Contrast requires finite samples with at least two observations")
    a, b = treatment.var(ddof=1) / len(treatment), control.var(ddof=1) / len(control)
    se = np.sqrt(a + b)
    effect = treatment.mean() - control.mean()
    if se == 0:
        return {"effect": float(effect), "se": 0., "ci_low": float(effect),
                "ci_high": float(effect), "p_value": float(effect == 0)}
    df = (a + b) ** 2 / (a * a / (len(treatment)-1) + b * b / (len(control)-1))
    critical = stats.t.ppf(1-alpha/2, df)
    return {"effect": float(effect), "se": float(se),
            "ci_low": float(effect-critical*se), "ci_high": float(effect+critical*se),
            "p_value": float(2*stats.t.sf(abs(effect/se), df))}


def standardized_difference(treatment, control):
    variance = (np.var(treatment, ddof=1) + np.var(control, ddof=1))/2
    difference = np.mean(treatment)-np.mean(control)
    return float(difference/np.sqrt(variance)) if variance > 0 else 0.

