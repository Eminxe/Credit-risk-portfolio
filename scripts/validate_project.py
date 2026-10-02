"""Run the same local evidence checks used by the manual CI job."""
import subprocess
import sys
from plata_risk.common import ROOT, OUTPUTS, timestamp, write_json

commands = [
    ["-m", "ruff", "check", "."],
    ["-m", "pytest", "-q"],
    ["scripts/verify_outputs.py"],
    ["scripts/verify_additional.py"],
    ["scripts/load_postgres.py"],
    ["scripts/load_additional_postgres.py"],
    ["scripts/load_postgres.py"],
    ["scripts/load_additional_postgres.py"],
    ["scripts/build_notebook.py"],
    ["scripts/execute_notebook.py"],
    ["scripts/export_reading_guides.py"],
]
receipt = {"status": "running", "started_at": timestamp(), "checks": []}
write_json(OUTPUTS / "validation_run.json", receipt)
for command in commands:
    print("Checking:", " ".join(command), flush=True)
    subprocess.run([sys.executable, *command], cwd=ROOT, check=True)
    receipt["checks"].append({"command": command, "status": "passed"})
receipt.update(status="passed", finished_at=timestamp())
write_json(OUTPUTS / "validation_run.json", receipt)
print("Validation, SQL load/idempotence and notebook execution passed")

