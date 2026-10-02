"""Store versioned aggregate evidence for the three additional source populations."""
import hashlib
import json
import pandas as pd
import psycopg
from psycopg.types.json import Jsonb
from plata_risk.common import ROOT, OUTPUTS, sha256

tables = {4: ["metrics", "policies"], 5: ["arm_summary", "ate", "email_economics"],
          6: ["vintages", "grade_summary", "grade_mix"]}
with psycopg.connect("") as conn, conn.cursor() as cur:
    cur.execute("""CREATE TABLE IF NOT EXISTS risk.additional_runs (
        run_id text PRIMARY KEY, case_number integer NOT NULL CHECK(case_number BETWEEN 4 AND 6),
        created_at timestamptz NOT NULL DEFAULT now(), metadata jsonb NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS risk.aggregate_results (
        run_id text REFERENCES risk.additional_runs(run_id), artifact text NOT NULL,
        row_number integer NOT NULL, payload jsonb NOT NULL,
        PRIMARY KEY (run_id, artifact, row_number))""")
    for case, names in tables.items():
        manifest = json.loads((OUTPUTS / f"case{case:02}_manifest.json").read_text())
        if manifest["status"] != "success":
            raise ValueError("Incomplete case")
        paths = [OUTPUTS / f"case{case:02}_{name}.csv" for name in names]
        hashes = {p.name: sha256(p) for p in paths}
        run = hashlib.sha256((json.dumps(hashes, sort_keys=True)+manifest["source"]["sha256"]+
                              sha256(ROOT / "configs/additional_cases.yaml")).encode()).hexdigest()
        cur.execute("INSERT INTO risk.additional_runs(run_id,case_number,metadata) VALUES(%s,%s,%s) "
                    "ON CONFLICT DO NOTHING", (run, case, Jsonb({"manifest": manifest, "hashes": hashes})))
        expected = 0
        for path in paths:
            records = json.loads(pd.read_csv(path).to_json(orient="records"))
            expected += len(records)
            cur.executemany("INSERT INTO risk.aggregate_results VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                            [(run, path.name, i, Jsonb(row)) for i, row in enumerate(records)])
        cur.execute("SELECT count(*) FROM risk.aggregate_results WHERE run_id=%s", (run,))
        if cur.fetchone()[0] != expected:
            raise ValueError("SQL aggregate reconciliation failed")
        print(f"Case {case:02}: verified {expected} aggregate records")

