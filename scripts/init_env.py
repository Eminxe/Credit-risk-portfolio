"""Create local secrets without printing them or replacing an existing .env."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if path.exists():
    print("Existing .env preserved")
else:
    text = (root / ".env.example").read_text()
    text = text.replace("POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n")
    text = text.replace("JUPYTER_TOKEN=\n", f"JUPYTER_TOKEN={secrets.token_urlsafe(32)}\n")
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)
    print("Created .env with random local secrets")
