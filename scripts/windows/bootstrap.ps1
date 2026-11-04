$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $RepoRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Python launcher (py) was not found. Install Python 3.12+ from python.org.' }
$PyVersion = & py -3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
$Parts = $PyVersion.Split('.')
if ([int]$Parts[0] -lt 3 -or ([int]$Parts[0] -eq 3 -and [int]$Parts[1] -lt 11)) { throw "Python 3.11+ required. Found $PyVersion" }
if (-not (Test-Path '.venv')) { & py -3 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e '.[test,monitoring,mcp]'
$StudioHome = Join-Path $env:LOCALAPPDATA '11vatedTech\AI-Game-Jam-Studio'
$env:STUDIO_HOME = $StudioHome
& .\.venv\Scripts\studio.exe init
& .\.venv\Scripts\studio.exe doctor
Write-Host "\nBootstrap complete. STUDIO_HOME=$StudioHome"
Write-Host 'Run: .\.venv\Scripts\studio.exe capabilities'
Write-Host 'Run: .\.venv\Scripts\studio.exe mcp serve'
