$ErrorActionPreference = 'Stop'
$PythonExe = 'D:\ProgramData\anaconda3\envs\mybase\python.exe'
$Builder = Join-Path $PSScriptRoot 'build_mvif_net_architecture.py'

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Project Python interpreter not found: $PythonExe"
}

& $PythonExe $Builder
if ($LASTEXITCODE -ne 0) {
    throw "MVIF-Net architecture build failed with exit code $LASTEXITCODE"
}
