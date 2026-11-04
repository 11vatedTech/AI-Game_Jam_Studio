$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $RepoRoot
if (-not (Test-Path '.venv\Scripts\pytest.exe')) { throw 'Run scripts\windows\bootstrap.ps1 first.' }
& .\.venv\Scripts\pytest.exe -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
