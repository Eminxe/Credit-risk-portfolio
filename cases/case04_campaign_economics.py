"""Pre-campaign response ranking with an ordered holdout; not causal uplift."""
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import yaml

from plata_risk.common import ROOT, OUTPUTS, sha256, timestamp, write_json
from plata_risk.credit import metrics
from plata_risk.sources import load_bank

EXCLUDED = ["y", "duration", "campaign", "contact", "day", "month"]


def model_for(name, x):
    categories = x.select_dtypes(include="object").columns.tolist()
    numeric = [c for c in x if c not in categories]
    prep = ColumnTransformer([("numeric", StandardScaler(), numeric),
                              ("categories", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categories)])
    learner = (LogisticRegression(max_iter=2500, C=1, random_state=42) if name=="logistic" else
               HistGradientBoostingClassifier(max_iter=120,max_leaf_nodes=15,learning_rate=.06,
                                               l2_regularization=5,early_stopping=False,random_state=42))
    # Expanding-window calibration: each calibration block follows its model's train block.
    groups = pd.util.hash_pandas_object(x, index=False).to_numpy()
    folds = []
    for train, valid in TimeSeriesSplit(3).split(x):
        train = train[~np.isin(groups[train], groups[valid])]
        folds.append((train, valid))
    return CalibratedClassifierCV(make_pipeline(prep,learner),cv=folds,method="sigmoid",n_jobs=1)


def main():
    write_json(OUTPUTS/"case04_manifest.json", {"status":"running"})
    frame, source = load_bank()
    s = yaml.safe_load((ROOT/"configs/additional_cases.yaml").read_text())["campaign"]
    if s["value_per_subscription"] <= 0 or s["cost_per_contact"] < 0:
        raise ValueError("Invalid campaign economics")
    x, y = frame.drop(columns=EXCLUDED), frame.y.eq("yes").astype(int)
    groups = pd.util.hash_pandas_object(x,index=False)
    cut1, cut2 = int(.6*len(x)), int(.8*len(x))
    hold = np.arange(cut2,len(x))
    valid = np.arange(cut1,cut2)
    # Avoid identical retained features bridging outer train/validation/test boundaries.
    hold_groups = set(groups.iloc[hold])
    valid = np.array([i for i in valid if groups[i] not in hold_groups])
    valid_groups, hold_groups = set(groups.iloc[valid]), set(groups.iloc[hold])
    train = np.array([i for i in range(cut1) if groups[i] not in valid_groups | hold_groups])
    dev = np.array([i for i in range(cut2) if groups[i] not in hold_groups])
    assert not set(groups.iloc[train]) & (valid_groups | hold_groups)
    assert not valid_groups & hold_groups
    candidates=[]
    for name in ["logistic","hist_gradient_boosting"]:
        print(f"Case 04 training {name}",flush=True)
        model=model_for(name,x.iloc[train]).fit(x.iloc[train],y.iloc[train])
        p=model.predict_proba(x.iloc[valid])[:,1]
        candidates.append({"model":name,"split":"ordered_validation",**metrics(y.iloc[valid],p)})
    selected=min(candidates,key=lambda row:row["log_loss"])["model"]
    model=model_for(selected,x.iloc[dev]).fit(x.iloc[dev],y.iloc[dev])
    p=model.predict_proba(x.iloc[hold])[:,1]
    candidates.append({"model":selected,"split":"ordered_holdout",**metrics(y.iloc[hold],p)})
    candidates.append({"model":"development_prevalence_baseline","split":"ordered_holdout",
                       **metrics(y.iloc[hold],np.full(len(hold), y.iloc[dev].mean()))})
    pd.DataFrame(candidates).rename(columns={"default_rate":"subscription_rate"}).to_csv(OUTPUTS/"case04_metrics.csv",index=False)
    scored=pd.DataFrame({"source_row":hold+1,"observed_subscription":y.iloc[hold].to_numpy(),"p_subscription":p})
    scored.to_csv(OUTPUTS/"case04_holdout_scores.csv",index=False)
    ranked=scored.sort_values(["p_subscription","source_row"],ascending=[False,True])
    policies=[]
    for fraction in s["contact_fractions"]:
        n=int(np.ceil(len(ranked)*fraction))
        policies.append((f"Top {fraction:.0%}",ranked.head(n)))
    policies.append(("Positive scenario EV",ranked[ranked.p_subscription*s["value_per_subscription"]>s["cost_per_contact"]]))
    summaries=[]
    for name, part in policies:
        summaries.append({"policy":name,"contacts":len(part),
                          "observed_subscriptions":int(part.observed_subscription.sum()),
                          "observed_rate":float(part.observed_subscription.mean()) if len(part) else 0.,
                          "model_expected_net_eur":float((part.p_subscription*s["value_per_subscription"]-s["cost_per_contact"]).sum()),
                          "retrospective_net_proxy_eur":float(part.observed_subscription.sum()*s["value_per_subscription"]-len(part)*s["cost_per_contact"])})
    policy=pd.DataFrame(summaries)
    policy.to_csv(OUTPUTS/"case04_policies.csv",index=False)
    from plata_risk.plots import plt, save
    plt.barh(policy.policy,policy.observed_rate*100,color="#244b68")
    plt.xlabel("Observed subscription rate among selected holdout records (%)")
    plt.title("UCI Bank Marketing | Response ranking, not causal uplift")
    save("case04_policy_response.png")
    joblib.dump(model,OUTPUTS/"case04_response_model.joblib")
    write_json(OUTPUTS/"case04_manifest.json",{
        "status":"success","finished_at":timestamp(),"source":source,"source_rows":len(frame),
        "development_rows":len(dev),"holdout_rows":len(hold),"validation_rows":len(valid),
        "selection_training_rows":len(train),
        "outer_feature_group_overlap":0,
        "development_subscription_rate":float(y.iloc[dev].mean()),
        "holdout_subscription_rate":float(y.iloc[hold].mean()),
        "selected_model":selected,"excluded_predictors":EXCLUDED,"assumptions":s,
        "selection":"Ordered validation log loss before final ordered holdout",
        "results_sha256":sha256(OUTPUTS/"case04_holdout_scores.csv"),
        "model_sha256":sha256(OUTPUTS/"case04_response_model.joblib"),
        "caveat":"Source row order is documented chronological, but exact dates and customer IDs are unavailable. Response among contacted clients is not treatment uplift; net values are scenario proxies.",
    })
    selected_result = next(row for row in candidates if row["model"] == selected and row["split"] == "ordered_holdout")
    print("Case 04 complete", selected_result, flush=True)


if __name__=="__main__":
    main()
