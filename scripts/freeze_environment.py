"""Record the tested Linux environment; editable project installed separately."""
import subprocess
import sys
from plata_risk.common import ROOT
lines = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True).splitlines()
lines = [line for line in lines if not line.startswith(("#", "-e", "plata-risk-casebook"))]
(ROOT / "requirements-linux.lock").write_text("\n".join(lines)+"\n")
print("Saved", len(lines), "tested package versions")

