$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    py -3 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python -m pip install -e "$Root[dev]"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Environment is ready."
Write-Host "Run: .\.venv\Scripts\recordtree.exe init"
