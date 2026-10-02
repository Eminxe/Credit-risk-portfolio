"""Original LendingClub 2007–2011 source snapshot, policy-eligible loans only."""
import pandas as pd
import yaml

from plata_risk.common import ROOT, OUTPUTS, timestamp, sha256, write_json
from plata_risk.portfolio import summarize_vintages
from plata_risk.sources import load_lendingclub


def main():
    write_json(OUTPUTS/"case06_manifest.json", {"status":"running"})
    frame, source = load_lendingclub()
    config = yaml.safe_load((ROOT/"configs/additional_cases.yaml").read_text())["portfolio"]
    excluded = frame.loan_status.str.startswith("Does not meet the credit policy")
    loans = frame[~excluded].copy()
    if len(loans) == 0:
        raise ValueError("No policy-eligible loans")
    vintage = summarize_vintages(loans, config["terminal_statuses"], config["bad_status"],
                                  config["minimum_terminal_coverage"], config["minimum_cohort_size"])
    vintage.to_csv(OUTPUTS/"case06_vintages.csv", index=False)
    loans["bad"] = loans.loan_status.eq(config["bad_status"])
    loans["terminal"] = loans.loan_status.isin(config["terminal_statuses"])
    grade = loans.groupby("grade").agg(n=("source_row","size"), originated_usd=("loan_amnt","sum"),
                                       bad_n=("bad","sum"), terminal_n=("terminal","sum"),
                                       mean_interest_rate=("interest_rate","mean")).reset_index()
    grade["terminal_chargeoff_rate"] = grade.bad_n/grade.terminal_n.replace(0,float("nan"))
    grade.to_csv(OUTPUTS/"case06_grade_summary.csv", index=False)
    mix = pd.crosstab(loans.issue_month,loans.grade,normalize="index")
    mix.to_csv(OUTPUTS/"case06_grade_mix.csv")
    from plata_risk.plots import plt, save
    plt.plot(vintage.issue_month,vintage.terminal_chargeoff_rate*100,color="#244b68",marker=".")
    plt.xlabel("Origination month (2007–2011)")
    plt.ylabel("Charged off / terminal loans (%)")
    plt.title("LendingClub | Terminal charge-off rate by vintage\nOnly cohorts with n ≥ 100 and terminal coverage ≥ 95%; gaps omitted")
    plt.xticks(rotation=0)
    save("case06_vintages.png")
    plt.bar(grade.grade, grade.terminal_chargeoff_rate*100,color="#244b68")
    plt.xlabel("Original LendingClub grade")
    plt.ylabel("Charged off / terminal loans (%)")
    plt.title("LendingClub | Observed terminal outcomes by grade")
    save("case06_grades.png")
    plt.plot(vintage.issue_month,vintage.originated_usd/1e6,color="#244b68")
    plt.xlabel("Origination month")
    plt.ylabel("Original principal (million USD)")
    plt.title("LendingClub | Origination volume")
    save("case06_volume.png")
    write_json(OUTPUTS/"case06_manifest.json",{
        "status":"success","finished_at":timestamp(),"source":source,
        "source_rows":len(frame),"policy_excluded_rows":int(excluded.sum()),"analyzed_rows":len(loans),
        "terminal_rows":int(loans.terminal.sum()),"charged_off_rows":int(loans.bad.sum()),
        "terminal_chargeoff_rate":float(loans.bad.sum()/loans.terminal.sum()),
        "origination_from":str(loans.issue_month.min().date()),"origination_to":str(loans.issue_month.max().date()),
        "cohort_count":len(vintage),"eligible_cohort_count":int(vintage.eligible.sum()),
        "assumptions":config,"results_sha256":sha256(OUTPUTS/"case06_vintages.csv"),
        "caveat":"Lifetime terminal status at an undated source snapshot; not fixed-horizon PD, causal grade effect or roll rates. No borrower IDs available.",
    })
    print(f"Case 06: {len(loans):,} loans; {loans.bad.sum():,} charged off; {vintage.eligible.sum()} eligible monthly cohorts",flush=True)


if __name__=="__main__":
    main()

