"""Execute with this Python, without requiring a global kernelspec installation."""
import json
import os
from pathlib import Path
import sys
import argparse

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--in-process", action="store_true",
                    help="Execute cells in a fresh IPython process when kernel ACL setup is unavailable")
args = parser.parse_args()
local = root / ".tmp/jupyter"
kernel = local / "kernels/plata312"
kernel.mkdir(parents=True, exist_ok=True)
runtime = local / "runtime"
runtime.mkdir(exist_ok=True)
(kernel / "kernel.json").write_text(json.dumps({
    "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
    "display_name": "Plata Python 3.12", "language": "python",
}))
recovery_share = Path(sys.prefix) / "Lib/site-packages/share/jupyter"
os.environ["JUPYTER_PATH"] = os.pathsep.join([str(local), str(recovery_share)])
os.environ["JUPYTER_RUNTIME_DIR"] = str(runtime)
os.environ["IPYTHONDIR"] = str(local / "ipython")
os.environ["MPLCONFIGDIR"] = str(root / ".tmp/matplotlib")
from nbclient import NotebookClient  # noqa: E402
from nbconvert import HTMLExporter  # noqa: E402
import nbformat  # noqa: E402

path = root / "notebooks/01_06_casebook.ipynb"
nb = nbformat.read(path, as_version=4)
if args.in_process:
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output
    shell = InteractiveShell.instance()
    os.chdir(root)
    count = 0
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        count += 1
        with capture_output(stdout=True, stderr=True, display=True) as captured:
            result = shell.run_cell(cell.source, store_history=True)
        result.raise_error()
        cell.execution_count = count
        cell.outputs = []
        for name in ["stdout", "stderr"]:
            value = getattr(captured, name)
            if value:
                cell.outputs.append(nbformat.v4.new_output("stream", name=name, text=value))
        for output in captured.outputs:
            cell.outputs.append(nbformat.v4.new_output("display_data", data=output.data,
                                                       metadata=output.metadata))
    nb.metadata["execution_mode"] = "Fresh in-process IPython; separate Jupyter kernel blocked by Windows ACL"
else:
    client = NotebookClient(nb, timeout=180, kernel_name="plata312", resources={"metadata": {"path": str(root)}})
    client.execute()
    nb.metadata["execution_mode"] = "Jupyter kernel"
nbformat.validate(nb)
nbformat.write(nb, path)
html, _ = HTMLExporter().from_notebook_node(nb)
(root / "outputs/casebook.html").write_text(html, encoding="utf-8")
print("Notebook executed and exported to outputs/casebook.html")
