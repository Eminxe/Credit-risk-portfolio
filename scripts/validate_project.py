"""Run the same local evidence checks used by the manual CI job."""
import subprocess
import sys
from plata_risk.common import ROOT, OUTPUTS, timestamp, write_json
from plata_risk.evidence import source_files, result_files, fingerprints

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
source_hashes = fingerprints(ROOT, source_files(ROOT))
write_json(OUTPUTS / "validation_run.json", receipt)
for command in commands:
    print("Checking:", " ".join(command), flush=True)
    subprocess.run([sys.executable, *command], cwd=ROOT, check=True)
    receipt["checks"].append({"command": command, "status": "passed"})
if source_hashes != fingerprints(ROOT, source_files(ROOT)):
    raise RuntimeError("Project source changed during validation; rerun with stable inputs")
receipt.update(status="passed", finished_at=timestamp(), source_sha256=source_hashes,
               result_sha256=fingerprints(ROOT, result_files(ROOT)))
write_json(OUTPUTS / "validation_run.json", receipt)
print("Validation, SQL load/idempotence and notebook execution passed")

