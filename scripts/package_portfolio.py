"""Package only defined project files after verifying current source/result hashes."""
import zipfile
from plata_risk.common import ROOT, OUTPUTS, sha256, timestamp, write_json
from plata_risk.evidence import source_files, result_files, fingerprints, require_current_validation

require_current_validation(ROOT)
receipts = [OUTPUTS / name for name in ["validation_run.json", "verification.json",
            "verification_additional.json", "infrastructure_verification.json"] if (OUTPUTS / name).exists()]
sources = fingerprints(ROOT, source_files(ROOT))
outputs = fingerprints(ROOT, result_files(ROOT) + receipts)
write_json(OUTPUTS / "artifact_index.json", {"packaged_at": timestamp(),
           "source_and_document_hashes": sources, "output_hashes": outputs,
           "raw_data": "Excluded; source receipts are embedded in case manifests",
           "secrets": "Only .env.example is included; local secrets and legacy files are excluded"})
target = ROOT / "deliverables"
target.mkdir(exist_ok=True)
archive = target / "Plata_Risk_Casebook_Portfolio.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in [*sources, *outputs, "outputs/artifact_index.json"]:
        z.write(ROOT / rel, "plata-risk-casebook/" + rel)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert all(not any(part.startswith(".env") and part != ".env.example" for part in name.split("/"))
               and "/data/raw/" not in name for name in z.namelist())
write_json(target / "package_receipt.json", {"filename": archive.name, "sha256": sha256(archive),
            "bytes": archive.stat().st_size, "created_at": timestamp()})
print(archive, archive.stat().st_size, "bytes; current evidence and ZIP integrity verified")
