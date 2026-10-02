"""Immutable cached download of UCI dataset 350; no synthetic fallback."""
import io
import json
import urllib.request
import zipfile

import numpy as np
import pandas as pd

from plata_risk.common import ROOT, sha256, timestamp, write_json

SOURCE = "https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip"
DOI = "https://doi.org/10.24432/C55S3H"
PAY = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
BILLS = [f"BILL_AMT{i}" for i in range(1, 7)]
PAYMENTS = [f"PAY_AMT{i}" for i in range(1, 7)]
FEATURES = ["LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE"] + PAY + BILLS + PAYMENTS


def load_uci():
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / "uci350.zip"
    receipt = raw / "uci350_source.json"
    if not archive.exists():
        req = urllib.request.Request(SOURCE, headers={"User-Agent": "PlataRiskCasebook/0.1"})
        with urllib.request.urlopen(req, timeout=120) as response:
            content = response.read()
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            if not any(name.endswith(".xls") for name in zf.namelist()):
                raise ValueError("UCI archive contains no XLS data")
        archive.write_bytes(content)
        write_json(receipt, {"url": SOURCE, "doi": DOI, "license": "CC BY 4.0",
                             "downloaded_at": timestamp(), "sha256": sha256(archive)})
    provenance = json.loads(receipt.read_text())
    if sha256(archive) != provenance["sha256"]:
        raise ValueError("Cached source hash changed")
    with zipfile.ZipFile(archive) as zf:
        names = [name for name in zf.namelist() if name.endswith(".xls")]
        df = pd.read_excel(io.BytesIO(zf.read(names[0])), header=1, engine="xlrd")
    df.columns = df.columns.astype(str).str.strip()
    df = df.rename(columns={"default payment next month": "default", "ID": "customer_id"})
    expected = {"customer_id", "default", *FEATURES}
    if set(df.columns) != expected or len(df) != 30000:
        raise ValueError(f"Unexpected UCI schema/size: {df.shape}, {list(df.columns)}")
    if df.isna().any().any() or df.customer_id.duplicated().any():
        raise ValueError("Missing values or duplicate customer IDs")
    if not set(df.default.unique()) <= {0, 1} or (df.LIMIT_BAL <= 0).any():
        raise ValueError("Invalid target or credit limit")
    if not np.isfinite(df.to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite source values")
    return df, provenance


def engineer(df):
    # Drop ID, target, sex and marital status. This is not a fairness certification.
    x = df[FEATURES].drop(columns=["SEX", "MARRIAGE"]).copy()
    x["EDUCATION"] = x.EDUCATION.where(x.EDUCATION.isin([1, 2, 3, 4]), 0)
    x["delinquent_months_6m"] = (df[PAY] > 0).sum(axis=1)
    x["bill_to_limit"] = df[BILLS].mean(axis=1) / df.LIMIT_BAL
    mean_bill = df[BILLS].mean(axis=1)
    x["payment_to_bill"] = df[PAYMENTS].mean(axis=1) / mean_bill.clip(lower=1)
    x["nonpositive_mean_bill"] = (mean_bill <= 0).astype(int)
    # Unknown repayment codes and negative bill balances are preserved and audited.
    return x
