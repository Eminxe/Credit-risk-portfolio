param([ValidateSet('test','pipeline','verify','notebook')][string]$Task = 'pipeline')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MPLCONFIGDIR = Join-Path (Get-Location) '.tmp/matplotlib'
$candidates = @($env:PLATA_PYTHON, '.venv/Scripts/python.exe', "$env:TEMP/plata-risk-py312/Scripts/python.exe")
$pythonExe = $null
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
        & $candidate -c 'import plata_risk, sklearn' 2>$null
        if ($LASTEXITCODE -eq 0) { $pythonExe = $candidate; break }
    }
}
if (-not $pythonExe) { throw 'Create a Python 3.12 environment and pip install -e .[dev], or set PLATA_PYTHON.' }
switch ($Task) {
    'test' {
        & $pythonExe -m ruff check src cases scripts tests
        if ($LASTEXITCODE -ne 0) { throw 'Lint failed' }
        & $pythonExe -m pytest -q -p no:cacheprovider
    }
    'pipeline' { & $pythonExe scripts/run_pipeline.py }
    'verify' { & $pythonExe scripts/verify_outputs.py }
    'notebook' { & $pythonExe scripts/build_notebook.py }
}
if ($LASTEXITCODE -ne 0) { throw "Task failed: $Task" }
