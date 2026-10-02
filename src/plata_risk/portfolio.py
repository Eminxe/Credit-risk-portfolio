"""Snapshot terminal outcomes; no fabricated loan-month transitions."""
import numpy as np
import pandas as pd


def summarize_vintages(frame, terminal_statuses, bad_status, minimum_coverage, minimum_size):
    work = frame.copy()
    work["terminal"] = work.loan_status.isin(terminal_statuses)
    work["bad"] = work.loan_status.eq(bad_status)
    result = work.groupby("issue_month").agg(
        n=("source_row","size"), originated_usd=("loan_amnt","sum"),
        mean_interest_rate=("interest_rate","mean"), terminal_n=("terminal","sum"), bad_n=("bad","sum"))
    result["terminal_coverage"] = result.terminal_n/result.n
    result["eligible"] = (result.terminal_coverage >= minimum_coverage) & (result.n >= minimum_size)
    result["terminal_chargeoff_rate"] = np.where(result.eligible & (result.terminal_n>0),
                                                 result.bad_n/result.terminal_n, np.nan)
    return result.reset_index()


def roll_rates(panel):
    required = {"account_id","month_end","state"}
    if not required <= set(panel):
        raise ValueError("True roll rates require account_id, month_end and state")
    frame = panel.copy()
    frame["month"] = pd.to_datetime(frame.month_end).dt.to_period("M")
    if frame.duplicated(["account_id","month"]).any():
        raise ValueError("Duplicate account-month")
    frame = frame.sort_values(["account_id","month"])
    frame["next_month"] = frame.groupby("account_id").month.shift(-1)
    frame["next_state"] = frame.groupby("account_id").state.shift(-1)
    adjacent = frame[frame.next_month == frame.month + 1]
    counts = adjacent.groupby(["state","next_state"]).size().rename("transitions").reset_index()
    counts["rate"] = counts.transitions/counts.groupby("state").transitions.transform("sum")
    return counts

