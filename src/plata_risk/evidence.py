"""Define the portable project boundary and reject stale validation receipts."""
import json
from pathlib import Path
from plata_risk.common import sha256

SOURCE_DIRS = {".devcontainer", ".github", ".vscode", "cases", "configs", "docker", "docs",
               "scripts", "sql", "src", "tests"}
ROOT_FILES = {".dockerignore", ".env.example", ".gitattributes", ".gitignore",
              "Dockerfile", "LICENSE", "Makefile", "pyproject.toml", "requirements-linux.lock"}
SOURCE_SUFFIXES = {".py", ".sh", ".ps1", ".json", ".sql", ".yaml", ".yml", ".toml", ".md",
                   ".png"}
OUTPUT_SUFFIXES = {".csv", ".json", ".html", ".png", ".parquet", ".joblib"}


def source_files(root):
    root = Path(root)
    files = [p for p in root.iterdir() if p.is_file() and
             (p.name in ROOT_FILES or p.suffix == ".md" and p.name != "AGENTS.md")]
    for directory in SOURCE_DIRS:
        for p in (root / directory).rglob("*"):
            if (p.is_file() and p.suffix in SOURCE_SUFFIXES
                    and "__pycache__" not in p.parts and not p.name.startswith(".env")):
                files.append(p)
    return sorted(files)


def result_files(root):
    root = Path(root)
    files = [p for p in (root / "outputs").glob("*") if p.is_file() and
             ((p.name.startswith("case0") and p.suffix in OUTPUT_SUFFIXES)
              or p.name in {"casebook.html", "portfolio_en.html", "explanation_ru.html"})]
    notebook = root / "notebooks/01_06_casebook.ipynb"
    if notebook.exists():
        files.append(notebook)
    return sorted(files)


def fingerprints(root, paths):
    return {p.relative_to(root).as_posix(): sha256(p) for p in paths}


def require_current_validation(root):
    root = Path(root)
    receipt = json.loads((root / "outputs/validation_run.json").read_text(encoding="utf-8"))
    expected = {"source_sha256": fingerprints(root, source_files(root)),
                "result_sha256": fingerprints(root, result_files(root))}
    if receipt.get("status") != "passed" or any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError("Validation is missing or stale; run scripts/validate_project.py before packaging")
    return receipt
