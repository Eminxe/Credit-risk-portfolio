"""Transactional and idempotent upload of verified current case artifacts."""
import hashlib
import json

import pandas as pd
import psycopg
from psycopg.types.json import Jsonb

from plata_risk.common import OUTPUTS, ROOT, load_scores, sha256


def main():
    scores, first = load_scores()
    second = json.loads((OUTPUTS / "case02_manifest.json").read_text())
    third = json.loads((OUTPUTS / "case03_manifest.json").read_text())
    scenario_hash = sha256(ROOT / "configs/scenarios.yaml")
    for manifest in [second, third]:
        if (manifest["status"] != "success" or manifest["case01_scores_sha256"] != first["scores_sha256"]
                or manifest["scenario_sha256"] != scenario_hash):
            raise ValueError("Stale downstream output")
    if second["npv_sha256"] != sha256(OUTPUTS / "case02_customer_npv.parquet"):
        raise ValueError("Case 02 file changed")
    if third["strategy_sha256"] != sha256(OUTPUTS / "case03_limit_strategy.parquet"):
        raise ValueError("Case 03 file changed")
    economics = pd.read_parquet(OUTPUTS / "case02_customer_npv.parquet")
    strategy = pd.read_parquet(OUTPUTS / "case03_limit_strategy.parquet")
    for frame in [economics, strategy]:
        if frame.customer_id.duplicated().any() or set(frame.customer_id) != set(scores.customer_id):
            raise ValueError("Cross-case customer mismatch")
    run_id = hashlib.sha256((first["scores_sha256"] + second["npv_sha256"] +
                             third["strategy_sha256"] + scenario_hash).encode()).hexdigest()
    # libpq reads PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD; no passwords in code.
    with psycopg.connect("") as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_setting('server_version_num')::int")
            version = cursor.fetchone()[0]
            if not 160000 <= version < 170000:
                raise ValueError(f"PostgreSQL 16 required, found version number {version}")
            cursor.execute("SELECT 1 FROM risk.runs WHERE run_id=%s", (run_id,))
            if cursor.fetchone():
                print("Verified run already loaded; preserved existing rows")
                return
            cursor.execute("INSERT INTO risk.runs(run_id,source_sha256,score_sha256,assumptions,metadata) "
                           "VALUES (%s,%s,%s,%s,%s)",
                           (run_id, first["source"]["sha256"], first["scores_sha256"],
                            Jsonb(second["assumptions"]), Jsonb({"case01": first, "case03": third})))
            with cursor.copy("COPY risk.customer_scores FROM STDIN") as copy:
                for row in scores.itertuples(index=False):
                    copy.write_row((run_id, row.customer_id, row.pd_1m, row.observed_default,
                                    row.prediction_type, row.LIMIT_BAL))
            with cursor.copy("COPY risk.customer_economics FROM STDIN") as copy:
                for row in economics.itertuples(index=False):
                    copy.write_row((run_id, row.customer_id, row.npv_twd, row.expected_loss_twd))
            with cursor.copy("COPY risk.limit_strategy FROM STDIN") as copy:
                for row in strategy.itertuples(index=False):
                    copy.write_row((run_id, row.customer_id, row.scenario_limit_twd,
                                    row.scenario_pd_1m, row.npv_twd, row.expected_loss_twd))
            for table in ["customer_scores", "customer_economics", "limit_strategy"]:
                cursor.execute(psycopg.sql.SQL("SELECT count(*) FROM risk.{} WHERE run_id=%s")
                               .format(psycopg.sql.Identifier(table)), (run_id,))
                if cursor.fetchone()[0] != len(scores):
                    raise ValueError("Upload count mismatch; transaction will roll back")
    print(f"Committed {len(scores)} customers in three tables; run={run_id}")


if __name__ == "__main__":
    main()
