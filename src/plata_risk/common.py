import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "outputs"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def load_scores():
    """Require the successful Case 01 manifest and matching artifact bytes."""
    import pandas as pd

    manifest = json.loads((OUTPUTS / "case01_manifest.json").read_text())
    path = OUTPUTS / "case01_scored_customers.parquet"
    if manifest["status"] != "success" or sha256(path) != manifest["scores_sha256"]:
        raise ValueError("Case 01 artifact is incomplete or has changed; rerun Case 01")
    scores = pd.read_parquet(path)
    if scores.customer_id.duplicated().any() or not scores.pd_1m.between(0, 1).all():
        raise ValueError("Invalid scored-customer contract")
    if set(scores.prediction_type) != {"out_of_fold", "holdout"}:
        raise ValueError("Downstream cases require predictions not fitted on the scored customer")
    return scores, manifest
