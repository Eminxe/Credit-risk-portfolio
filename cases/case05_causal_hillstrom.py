"""Two email arms versus randomized no-email control, all assigned customers."""
import numpy as np
import pandas as pd
from scipy.stats import chisquare
from statsmodels.stats.multitest import multipletests
import yaml

from plata_risk.common import ROOT, OUTPUTS, sha256, timestamp, write_json
from plata_risk.experiment import mean_contrast, standardized_difference
from plata_risk.sources import load_hillstrom


def main():
    write_json(OUTPUTS/"case05_manifest.json", {"status": "running"})
    frame, source = load_hillstrom()
    s = yaml.safe_load((ROOT/"configs/additional_cases.yaml").read_text())["experiment"]
    if not 0 < s["alpha"] < 1 or not 0 <= s["contribution_margin"] <= 1 or s["cost_per_email"] < 0:
        raise ValueError("Invalid experiment scenario")
    control = frame[frame.segment == "No E-Mail"]
    summaries = frame.groupby("segment").agg(n=("visit", "size"), visit_rate=("visit","mean"),
                                              conversion_rate=("conversion","mean"), mean_spend_usd=("spend","mean"))
    summaries.to_csv(OUTPUTS/"case05_arm_summary.csv")
    effects, balance = [], []
    covariates = pd.get_dummies(frame[["recency","history","mens","womens","newbie","zip_code","channel"]],
                                 columns=["zip_code","channel"], dtype=float)
    for arm in ["Mens E-Mail", "Womens E-Mail"]:
        treatment = frame[frame.segment == arm]
        for outcome in ["visit", "conversion", "spend"]:
            effects.append({"arm": arm, "outcome": outcome, "n_treatment": len(treatment),
                            "n_control": len(control), **mean_contrast(treatment[outcome], control[outcome], s["alpha"])})
        for column in covariates:
            balance.append({"arm": arm, "covariate": column,
                            "standardized_mean_difference": standardized_difference(
                                covariates.loc[frame.segment==arm,column], covariates.loc[frame.segment=="No E-Mail",column])})
    effects = pd.DataFrame(effects)
    effects["p_holm"] = multipletests(effects.p_value, method="holm")[1]
    effects["significant_holm"] = effects.p_holm < s["alpha"]
    effects.to_csv(OUTPUTS/"case05_ate.csv", index=False)
    pd.DataFrame(balance).to_csv(OUTPUTS/"case05_baseline_balance.csv", index=False)
    economics = effects[effects.outcome=="spend"].copy()
    for field in ["effect","ci_low","ci_high"]:
        economics["net_contribution_"+field] = economics[field]*s["contribution_margin"]-s["cost_per_email"]
    economics.to_csv(OUTPUTS/"case05_email_economics.csv", index=False)
    from plata_risk.plots import plt, save
    for i, outcome in enumerate(["visit", "conversion", "spend"]):
        part = effects[effects.outcome==outcome]
        fig, ax = plt.subplots(figsize=(9, 3.6))
        scale = 100 if outcome != "spend" else 1
        ax.errorbar(part.effect*scale, [0,1],
                    xerr=np.vstack([(part.effect-part.ci_low)*scale, (part.ci_high-part.effect)*scale]),
                    fmt="o", capsize=5, color="#244b68")
        ax.axvline(0, color="gray", linestyle="--")
        ax.set_yticks([0,1], ["Men's email", "Women's email"])
        ax.set_ylim(-.6, 1.6)
        ax.set_xlabel("Difference versus no email ("+("percentage points" if scale==100 else "USD/customer")+")")
        ax.set_title(f"Hillstrom | Two-week {outcome} effect | pointwise 95% CI")
        save(f"case05_{outcome}_effect.png")
    write_json(OUTPUTS/"case05_manifest.json", {
        "status":"success", "finished_at":timestamp(), "source":source, "rows":len(frame),
        "arm_counts":{k:int(v) for k,v in frame.segment.value_counts().items()},
        "allocation_chi_square_p":float(chisquare(frame.segment.value_counts()).pvalue),
        "max_abs_baseline_smd":max(abs(row["standardized_mean_difference"]) for row in balance),
        "assumptions":s, "results_sha256":sha256(OUTPUTS/"case05_ate.csv"),
        "inference":"Intent-to-treat mean differences, Welch pointwise CIs; Holm p-values across six contrasts",
        "caveat":"Randomization relies on the source design description; effects concern this retailer and two-week window",
    })
    print("Case 05: randomized experiment", effects[["arm","outcome","effect","p_holm"]].to_string(index=False), flush=True)


if __name__=="__main__":
    main()

