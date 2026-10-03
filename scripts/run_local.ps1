param([ValidateSet('setup','test','pipeline','verify','notebook','validate','package','jupyter','down')]
      [string]$Task = 'pipeline')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker task failed: $Task (exit $LASTEXITCODE)" }
}
function Invoke-Analytics([string]$Script) {
    Invoke-Docker compose run --rm analytics python $Script
}
switch ($Task) {
    'setup' {
        $baseImage = ((Get-Content Dockerfile | Where-Object { $_ -match '^FROM ' } | Select-Object -First 1) -split '\s+')[1]
        Invoke-Docker run --rm --mount "type=bind,source=$((Get-Location).Path),target=/workspace" -w /workspace $baseImage python scripts/init_env.py
        Invoke-Docker compose config --quiet
        Invoke-Docker compose build analytics
        Invoke-Docker compose up -d --wait postgres
    }
    'test' { Invoke-Docker compose run --rm analytics bash scripts/test.sh }
    'pipeline' { Invoke-Analytics 'scripts/run_pipeline.py' }
    'verify' {
        Invoke-Analytics 'scripts/verify_outputs.py'
        Invoke-Analytics 'scripts/verify_additional.py'
    }
    'notebook' {
        Invoke-Analytics 'scripts/build_notebook.py'
        Invoke-Analytics 'scripts/execute_notebook.py'
        Invoke-Analytics 'scripts/export_reading_guides.py'
    }
    'validate' { Invoke-Analytics 'scripts/validate_project.py' }
    'package' { Invoke-Analytics 'scripts/package_portfolio.py' }
    'jupyter' {
        Invoke-Docker compose up -d --wait jupyter
        Invoke-Docker compose exec -T jupyter python scripts/jupyter_ready.py
    }
    'down' { Invoke-Docker compose down }
}
