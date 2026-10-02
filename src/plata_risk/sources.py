"""Download original public sources with immutable cached receipts and hashes."""
import io
import json
import urllib.request
import zipfile

import pandas as pd

from plata_risk.common import ROOT, sha256, timestamp, write_json

SOURCES = {
    "bank": {"url": "https://archive.ics.uci.edu/static/public/222/bank%2Bmarketing.zip",
             "filename": "uci222.zip", "citation": "https://doi.org/10.24432/C5K306",
             "license": "CC BY 4.0"},
    "hillstrom": {"url": "http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv",
                  "filename": "hillstrom.csv",
                  "citation": "https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html",
                  "license": "Public research challenge; redistribution license not established"},
    "lendingclub": {"url": "https://resources.lendingclub.com/LoanStats3a.csv.zip",
                    "filename": "LoanStats3a.csv.zip",
                    "citation": "https://resources.lendingclub.com/LoanStats3a.csv.zip",
                    "license": "Original public LendingClub loan statistics; redistribution license not established"},
}


def cached_source(name):
    spec = SOURCES[name]
    path = ROOT / "data/raw" / spec["filename"]
    receipt = path.with_suffix(path.suffix + ".source.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        request = urllib.request.Request(spec["url"], headers={"User-Agent": "PlataRiskCasebook/0.2"})
        with urllib.request.urlopen(request, timeout=180) as response:
            payload, resolved_url = response.read(), response.url
        if spec["filename"].endswith(".zip") and not zipfile.is_zipfile(io.BytesIO(payload)):
            raise ValueError(f"{name}: expected a ZIP source")
        if payload.lstrip().lower().startswith((b"<!doctype", b"<html")):
            raise ValueError(f"{name}: source returned HTML instead of data")
        path.write_bytes(payload)
        write_json(receipt, {**spec, "resolved_url": resolved_url,
                             "downloaded_at": timestamp(), "sha256": sha256(path)})
    metadata = json.loads(receipt.read_text())
    if metadata["sha256"] != sha256(path):
        raise ValueError(f"{name}: cached source was modified")
    return path, metadata


def load_bank():
    path, meta = cached_source("bank")
    with zipfile.ZipFile(path) as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read("bank.zip"))) as inner:
            frame = pd.read_csv(io.BytesIO(inner.read("bank-full.csv")), sep=";")
    if len(frame) != 45211 or len(frame.columns) != 17 or frame.isna().any().any():
        raise ValueError("Unexpected Bank Marketing dataset size/schema/missingness")
    if set(frame.y.unique()) != {"yes", "no"}:
        raise ValueError("Unexpected bank outcome")
    return frame, meta


def load_hillstrom():
    path, meta = cached_source("hillstrom")
    frame = pd.read_csv(path)
    frame.columns = frame.columns.str.lower()
    expected = {"recency", "history_segment", "history", "mens", "womens", "zip_code",
                "newbie", "channel", "segment", "visit", "conversion", "spend"}
    if len(frame) != 64000 or set(frame.columns) != expected or frame.isna().any().any():
        raise ValueError("Unexpected Hillstrom source")
    if set(frame.segment) != {"Mens E-Mail", "Womens E-Mail", "No E-Mail"}:
        raise ValueError("Unexpected experimental arms")
    for field in ["visit", "conversion", "mens", "womens", "newbie"]:
        if not set(frame[field].unique()) <= {0, 1}:
            raise ValueError(f"Nonbinary {field}")
    if (frame.spend < 0).any() or (frame.conversion > frame.visit).any():
        raise ValueError("Inconsistent Hillstrom outcomes")
    return frame, meta


def load_lendingclub():
    path, meta = cached_source("lendingclub")
    keep = ["id", "loan_amnt", "term", "int_rate", "grade", "sub_grade", "issue_d",
            "loan_status", "last_pymnt_d"]
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".csv"))
        # Original first line is a download/snapshot annotation, not a column header.
        payload = archive.read(name)
        first = payload.splitlines()[0].decode("utf-8", errors="replace")
        skip = 0 if "loan_amnt" in first else 1
        frame = pd.read_csv(io.BytesIO(payload), skiprows=skip,
                            usecols=lambda col: col in keep, low_memory=False)
    frame["loan_amnt"] = pd.to_numeric(frame.loan_amnt, errors="coerce")
    footer_rows = int(frame.loan_amnt.isna().sum())
    frame = frame[frame.loan_amnt.notna()].copy()
    if (frame.loan_amnt <= 0).any() or frame[["issue_d", "loan_status", "grade"]].isna().any().any():
        raise ValueError("Invalid LendingClub core fields")
    frame["issue_month"] = pd.to_datetime(frame.issue_d, format="%b-%Y", errors="raise")
    frame["interest_rate"] = frame.int_rate.str.strip().str.rstrip("%").astype(float) / 100
    frame["term_months"] = frame.term.str.extract(r"(\d+)")[0].astype(int)
    if not frame.term_months.isin([36, 60]).all():
        raise ValueError("Unknown contractual term")
    if not frame.interest_rate.between(0, 1).all():
        raise ValueError("Invalid interest rate")
    meta = {**meta, "source_header": first, "footer_rows_removed": footer_rows,
            "id_available": "id" in frame and bool(frame.id.notna().all())}
    # Synthetic sequential key labels source rows only; no invented customer data.
    frame["source_row"] = range(1, len(frame) + 1)
    return frame, meta
