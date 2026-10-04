"""Run real UCI data -> grouped nested-CV PD -> untouched holdout metrics."""
import importlib.metadata
import os

os.environ.setdefault("OMP_NUM_THREADS", "2")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import joblib  # noqa: E402

from plata_risk.common import OUTPUTS, sha256, timestamp, write_json  # noqa: E402
from plata_risk.credit import calibrated_model, grouped_splits, metrics, risk_deciles  # noqa: E402
from plata_risk.data import BILLS, PAY, engineer, load_uci  # noqa: E402


def main():
    OUTPUTS.mkdir(exist_ok=True)
    write_json(OUTPUTS / "case01_manifest.json", {"status": "running", "started_at": timestamp()})
    df, source = load_uci()
    x, y = engineer(df), df.default
    groups = pd.util.hash_pandas_object(x, index=False).to_numpy()
    dev, hold = grouped_splits(x, y, groups, n=5)[0]
    xd, yd, gd = x.iloc[dev].reset_index(drop=True), y.iloc[dev].reset_index(drop=True), groups[dev]
    assert not set(gd) & set(groups[hold])
    folds = grouped_splits(xd, yd, gd)
    oof, fitted, rows = {}, {}, []
    for name in ["logistic", "hist_gradient_boosting"]:
        print(f"Training {name}: grouped out-of-fold predictions and sigmoid calibration", flush=True)
        p = np.full(len(dev), np.nan)
        for train, valid in folds:
            assert not set(gd[train]) & set(gd[valid])
            model = calibrated_model(name, xd.iloc[train], yd.iloc[train], gd[train])
            model.fit(xd.iloc[train], yd.iloc[train])
            p[valid] = model.predict_proba(xd.iloc[valid])[:, 1]
        assert np.isfinite(p).all()
        oof[name] = p
        rows.append({"model": name, "split": "development_oof", **metrics(yd, p)})
        model = calibrated_model(name, xd, yd, gd)
        fitted[name] = model.fit(xd, yd)
    # Select BEFORE accessing holdout labels; OOF results are model-selection data.
    selected = min(rows, key=lambda row: row["log_loss"])["model"]
    hold_predictions = {}
    for name, model in fitted.items():
        p = model.predict_proba(x.iloc[hold])[:, 1]
        hold_predictions[name] = p
        rows.append({"model": name, "split": "holdout", **metrics(y.iloc[hold], p)})
    pd.DataFrame(rows).to_csv(OUTPUTS / "case01_model_metrics.csv", index=False)
    scored = df.rename(columns={"default": "observed_default"}).copy()
    scored["pd_1m"] = np.nan
    scored["prediction_type"] = "out_of_fold"
    scored.loc[dev, "pd_1m"] = oof[selected]
    scored.loc[hold, "pd_1m"] = hold_predictions[selected]
    scored.loc[hold, "prediction_type"] = "holdout"
    scored["model"] = selected
    scored["feature_group"] = groups.astype(str)
    scored.to_parquet(OUTPUTS / "case01_scored_customers.parquet", index=False)
    scored.to_csv(OUTPUTS / "case01_scored_customers.csv", index=False)
    joblib.dump(fitted[selected], OUTPUTS / "case01_credit_model.joblib")
    from plata_risk.diagnostics import grouped_bootstrap, subgroup_diagnostics
    grouped_bootstrap(y.iloc[hold], hold_predictions[selected], groups[hold]).to_csv(
        OUTPUTS / "case01_uncertainty.csv", index=False)
    subgroup_diagnostics(scored.iloc[hold]).to_csv(OUTPUTS / "case01_subgroups.csv", index=False)
    pd.DataFrame({"customer_id": df.iloc[hold].customer_id.to_numpy(),
                  "observed_default": y.iloc[hold].to_numpy(), **hold_predictions}).to_csv(
        OUTPUTS / "case01_holdout_predictions.csv", index=False)
    from plata_risk.scorecard import information_values, stability_report
    # Scorecard diagnostics use development rows only for IV; PSI compares holdout to development.
    iv, woe = information_values(xd, yd)
    iv.to_csv(OUTPUTS / "case01_information_value.csv", index=False)
    woe.to_csv(OUTPUTS / "case01_woe_bins.csv", index=False)
    reference = xd.assign(score_pd_1m=oof[selected])
    current = x.iloc[hold].reset_index(drop=True).assign(score_pd_1m=hold_predictions[selected])
    stability_report(reference, current, ["score_pd_1m", *x.columns]).to_csv(
        OUTPUTS / "case01_stability.csv", index=False)
    deciles = risk_deciles(y.iloc[hold], hold_predictions[selected])
    deciles.to_csv(OUTPUTS / "case01_risk_deciles.csv", index=False)
    audit = {"rows": len(df), "source_features": 23, "missing_cells": int(df.isna().sum().sum()),
             "default_count": int(y.sum()), "development_rows": len(dev), "holdout_rows": len(hold),
             "duplicate_feature_rows": int(x.duplicated().sum()),
             "negative_bill_cells": int((df[BILLS] < 0).sum().sum()),
             "education_codes": {str(k): int(v) for k, v in df.EDUCATION.value_counts().items()},
             "repayment_codes": sorted(int(v) for v in np.unique(df[PAY].to_numpy())),
             "group_overlap": len(set(gd) & set(groups[hold])),
             "excluded_predictors": ["customer_id", "default", "SEX", "MARRIAGE"],
             "scope": "Taiwan 2005 behavioral default-payment prediction, not Plata data or IFRS9 PD",
             "validation": "Grouped random holdout, not out-of-time validation"}
    write_json(OUTPUTS / "case01_data_audit.json", audit)
    from plata_risk.plots import credit_plots
    credit_plots(y.iloc[hold], hold_predictions, deciles)
    write_json(OUTPUTS / "case01_manifest.json", {
        "status": "success", "finished_at": timestamp(), "source": source,
        "selected_model": selected, "selection": "minimum development OOF log loss",
        "scores_sha256": sha256(OUTPUTS / "case01_scored_customers.parquet"),
        "model_sha256": sha256(OUTPUTS / "case01_credit_model.joblib"),
        "seed": 42, "versions": {p: importlib.metadata.version(p) for p in
                                 ["numpy", "pandas", "scipy", "scikit-learn", "pyarrow"]},
    })
    print(pd.DataFrame(rows).to_string(index=False), flush=True)
    print(f"Case 01 succeeded; selected model: {selected}")


if __name__ == "__main__":
    main()
