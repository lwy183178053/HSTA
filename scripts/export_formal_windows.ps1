[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$DatazooWorkers = 'auto',
    [int]$DatazooBatchSize = 2048,
    [int]$DatazooTestBatchSize = 2048,
    [int]$TopK = 60,
    [int]$MaxTrainPerClass = 10000,
    [int]$MaxValPerClass = 2000,
    [int]$MaxTestPerClass = 2000,
    [double]$NoiseRatio = 0.10,
    [double]$UnknownRatio = 0.30
)

$ErrorActionPreference = 'Stop'
$python = if ($env:HSTA_WINDOWS_PYTHON) {
    $env:HSTA_WINDOWS_PYTHON
} else {
    'D:\ProgramData\anaconda3\envs\mybase\python.exe'
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Windows Python was not found: $python. Set HSTA_WINDOWS_PYTHON to the project interpreter."
}
if ($DatazooWorkers -ne 'auto' -and $DatazooWorkers -notmatch '^[0-9]+$') {
    throw "DatazooWorkers must be 'auto' or a non-negative integer."
}
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$processed = Join-Path $root 'data\processed'
New-Item -ItemType Directory -Force -Path $processed | Out-Null
Push-Location $root
try {

foreach ($dataset in @('tls', 'quic')) {
    $outCsv = Join-Path $processed "datazoo_${dataset}60_s_protocol.csv"
    Write-Host "[$(Get-Date -Format o)] export $dataset with Windows Python, workers=$DatazooWorkers"
    & $python -m data.preprocess `
        --project-root $root `
        --dataset $dataset `
        --size S `
        --topk $TopK `
        --max-train-per-class $MaxTrainPerClass `
        --max-val-per-class $MaxValPerClass `
        --max-test-per-class $MaxTestPerClass `
        --noise-ratio $NoiseRatio `
        --unknown-ratio $UnknownRatio `
        --datazoo-workers $DatazooWorkers `
        --datazoo-batch-size $DatazooBatchSize `
        --datazoo-test-batch-size $DatazooTestBatchSize `
        --out-csv $outCsv
    if ($LASTEXITCODE -ne 0) {
        throw "Data export failed for $dataset with exit code $LASTEXITCODE"
    }

    & $python (Join-Path $root 'scripts\audit_open_set_dataset.py') `
        --input-csv $outCsv `
        --expected-known $TopK
    if ($LASTEXITCODE -ne 0) {
        throw "Dataset audit failed for $dataset with exit code $LASTEXITCODE"
    }
}

Write-Host "[$(Get-Date -Format o)] formal Windows export completed"
} finally {
    Pop-Location
}
