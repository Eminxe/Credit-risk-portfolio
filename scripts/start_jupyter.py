"""Start Jupyter without shadowing the installed jupyter_server package."""
import os
from jupyterlab.labapp import LabApp
from traitlets.config import Config

token = os.environ.get("JUPYTER_TOKEN")
if not token:
    raise SystemExit("Set a nonempty JUPYTER_TOKEN in .env")
config = Config()
config.IdentityProvider.token = token
LabApp.launch_instance(config=config, argv=[
    "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root",
])
