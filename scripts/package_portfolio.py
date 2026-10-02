"""Package reviewable source and evidence without secrets or raw datasets."""
import json
import zipfile
from plata_risk.common import ROOT, OUTPUTS, sha256, timestamp, write_json

validation = json.loads((OUTPUTS / "validation_run.json").read_text())
if validation["status"] != "passed":
    raise ValueError("Complete validation before packaging")
excluded = {".git", ".venv", ".tmp", "__pycache__", ".pytest_cache", ".ruff_cache",
            ".ipynb_checkpoints", "deliverables"}
sources, outputs = {}, {}
for path in ROOT.rglob("*"):
    rel = path.relative_to(ROOT)
    if not path.is_file() or any(p in excluded or p.endswith(".egg-info") for p in rel.parts):
        continue
    if path.name == ".env" or path.suffix == ".log" or (rel.parts[0:2] == ("data", "raw")):
        continue
    if rel.as_posix() == "outputs/artifact_index.json":
        continue
    if rel.as_posix() == "notebooks/01_03_casebook.ipynb":
        continue  # Previous local edition; ship the current six-case notebook only.
    (outputs if rel.parts[0] == "outputs" else sources)[rel.as_posix()] = sha256(path)
write_json(OUTPUTS / "artifact_index.json", {"packaged_at": timestamp(),
           "source_and_document_hashes": sources, "output_hashes": outputs,
           "raw_data": "Excluded; original-source download scripts and receipts embedded in case manifests",
           "secrets": "Excluded"})
target = ROOT / "deliverables"
target.mkdir(exist_ok=True)
archive = target / "Plata_Risk_Casebook_Portfolio.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in [*sources, *outputs, "outputs/artifact_index.json"]:
        z.write(ROOT / rel, "plata-risk-casebook/"+rel)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert not any(name.endswith("/.env") or "/data/raw/" in name for name in z.namelist())
write_json(target / "package_receipt.json", {"filename": archive.name, "sha256": sha256(archive),
            "bytes": archive.stat().st_size, "created_at": timestamp()})
print(archive, archive.stat().st_size, "bytes; integrity checked; no secrets or raw datasets")

