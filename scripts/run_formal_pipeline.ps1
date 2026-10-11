[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$DatazooWorkers = 'auto',
    [int]$DatazooBatchSize = 2048,
    [int]$DatazooTestBatchSize = 2048
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$exportScript = Join-Path $root 'scripts\export_formal_windows.ps1'
$python = if ($env:HSTA_WINDOWS_PYTHON) {
    $env:HSTA_WINDOWS_PYTHON
} else {
    'D:\ProgramData\anaconda3\envs\mybase\python.exe'
}

& $python --version
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $exportScript `
    -ProjectRoot $root `
    -DatazooWorkers $DatazooWorkers `
    -DatazooBatchSize $DatazooBatchSize `
    -DatazooTestBatchSize $DatazooTestBatchSize
if ($LASTEXITCODE -ne 0) {
    throw "Windows data export failed with exit code $LASTEXITCODE"
}

# Translate the repository path without depending on WSL interop from inside
# WSL. The training process itself stays in the supported Ubuntu environment.
$drive = $root.Substring(0, 1).ToLowerInvariant()
$rest = ($root.Substring(2) -replace '\\', '/')
$wslRoot = "/mnt/$drive$rest"
Write-Host "[$(Get-Date -Format o)] starting WSL acceptance and training"
& wsl.exe -d Ubuntu-22.04 -- bash -lc "cd '$wslRoot' && export SKIP_DATA_EXPORT=1 && bash scripts/run_formal_pipeline.sh"
if ($LASTEXITCODE -ne 0) {
    throw "WSL training pipeline failed with exit code $LASTEXITCODE"
}
