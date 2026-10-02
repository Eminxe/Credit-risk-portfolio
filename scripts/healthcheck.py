"""Authenticated Jupyter and PostgreSQL checks; never print access secrets."""
import json
import os
import urllib.request
import psycopg
from plata_risk.common import OUTPUTS, timestamp, write_json

token = os.environ["JUPYTER_TOKEN"]
request = urllib.request.Request("http://jupyter:8888/api/status",
                                 headers={"Authorization": "token "+token})
with urllib.request.urlopen(request, timeout=20) as response:
    status = json.load(response)
assert "kernels" in status
with psycopg.connect("") as conn, conn.cursor() as cur:
    cur.execute("SELECT current_setting('server_version')")
    version = cur.fetchone()[0]
    counts = {}
    for table in ["customer_scores", "customer_economics", "limit_strategy", "aggregate_results"]:
        cur.execute(psycopg.sql.SQL("SELECT count(*) FROM risk.{}").format(psycopg.sql.Identifier(table)))
        counts[table] = cur.fetchone()[0]
write_json(OUTPUTS / "infrastructure_verification.json",
           {"status": "passed", "verified_at": timestamp(), "postgres_version": version,
            "jupyter_authenticated_http": 200, "table_counts": counts})
print("PostgreSQL", version, "| Authenticated Jupyter HTTP 200 | SQL counts", counts)

