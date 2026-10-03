import json
import pytest
from plata_risk.evidence import (fingerprints, source_files, result_files, require_current_validation)


def fixture_project(root):
    (root / "src").mkdir()
    (root / "src/model.py").write_text("value = 1")
    (root / "outputs").mkdir()
    (root / "outputs/case01_metrics.csv").write_text("score\n0.8\n")
    receipt = {"status": "passed", "source_sha256": fingerprints(root, source_files(root)),
               "result_sha256": fingerprints(root, result_files(root))}
    (root / "outputs/validation_run.json").write_text(json.dumps(receipt))


@pytest.mark.parametrize("changed", ["src/model.py", "outputs/case01_metrics.csv"])
def test_packaging_rejects_changes_after_validation(tmp_path, changed):
    fixture_project(tmp_path)
    require_current_validation(tmp_path)
    (tmp_path / changed).write_text("changed after validation")
    with pytest.raises(ValueError, match="stale"):
        require_current_validation(tmp_path)


def test_package_boundary_excludes_backups_and_legacy(tmp_path):
    fixture_project(tmp_path)
    (tmp_path / ".env.backup").write_text("secret")
    (tmp_path / ".env.example").write_text("TOKEN=")
    (tmp_path / "requirements-local-windows.lock").write_text("legacy")
    (tmp_path / ".tmp").mkdir()
    (tmp_path / ".tmp/old.py").write_text("legacy")
    included = {p.relative_to(tmp_path).as_posix() for p in source_files(tmp_path)}
    assert ".env.example" in included
    assert not {".env.backup", ".tmp/old.py", "requirements-local-windows.lock"} & included
