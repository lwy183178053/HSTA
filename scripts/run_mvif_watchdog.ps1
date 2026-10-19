[CmdletBinding()]
param(
    [string]$Distro = 'Ubuntu-22.04',
    [int]$RetryDelaySeconds = 45,
    [int]$MaxAttempts = 0
)

# This host-side loop survives a WSL or CUDA process reset.  Every retry uses
# run_experiments.py --resume, so completed runs are skipped and interrupted
# runs continue from their latest checkpoint.
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$wslRepoRoot = ($repoRoot -replace '\\', '/')
if ($wslRepoRoot -notmatch '^([A-Za-z]):/(.*)$') {
    throw "Expected a drive-letter repository path, got: $repoRoot"
}
$wslRepoRoot = "/mnt/$($matches[1].ToLowerInvariant())/$($matches[2])"

$runNames = @(
    'mvif_net_open_tls60_seed599',
    'mvif_net_open_tls60_seed5009',
    'mvif_net_open_tls60_seed813',
    'mvif_net_open_quic60_seed599',
    'mvif_net_open_quic60_seed5009',
    'mvif_net_open_quic60_seed813',
    'mvif_net_closed_tls60_seed599',
    'mvif_net_closed_tls60_seed5009',
    'mvif_net_closed_tls60_seed813',
    'mvif_net_closed_quic60_seed599',
    'mvif_net_closed_quic60_seed5009',
    'mvif_net_closed_quic60_seed813'
)

$resultsRoot = Join-Path $repoRoot 'results\mvif_net_masked_global_pooling'
$logPath = Join-Path $repoRoot 'logs\mvif_watchdog.log'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null

function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff zzz'
    Add-Content -LiteralPath $logPath -Value "[$stamp] $Message" -Encoding UTF8
}

function Get-MissingRuns {
    @($runNames | Where-Object {
        $runDir = Join-Path $resultsRoot $_
        -not ((Test-Path -LiteralPath (Join-Path $runDir 'summary.csv')) -and
              (Test-Path -LiteralPath (Join-Path $runDir 'metrics.json')))
    })
}

$mutex = [Threading.Mutex]::new($false, 'Local\MVIF-Net-Queue-Watchdog')
$ownsMutex = $false
try {
    try {
        $ownsMutex = $mutex.WaitOne(0)
    } catch [Threading.AbandonedMutexException] {
        $ownsMutex = $true
    }
    if (-not $ownsMutex) {
        Write-Log 'another watchdog instance is already running; exiting'
        exit 0
    }

    $attempt = 0
    while ($true) {
        $missing = Get-MissingRuns
        if ($missing.Count -eq 0) {
            Write-Log 'all 12 MVIF-Net runs have summary.csv and metrics.json; queue complete'
            break
        }
        if ($MaxAttempts -gt 0 -and $attempt -ge $MaxAttempts) {
            Write-Log "maximum retry count reached: $MaxAttempts; remaining: $($missing -join ', ')"
            exit 1
        }

        $attempt++
        Write-Log "attempt $attempt; remaining: $($missing -join ', ')"
        $onlyArgs = $runNames -join ' '
        $bashCommand = "cd '$wslRepoRoot' && source /opt/traffic-mamba-venv/bin/activate && python -u run_experiments.py --config configs/compact_s.yaml --resume --only $onlyArgs"

        & wsl.exe -d $Distro -- bash -lc $bashCommand 2>&1 | ForEach-Object {
            $line = [string]$_
            Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
        }
        $exitCode = $LASTEXITCODE
        $remainingAfter = Get-MissingRuns
        Write-Log "attempt $attempt exited with code $exitCode; remaining after retry: $($remainingAfter -join ', ')"

        if ($remainingAfter.Count -eq 0) {
            Write-Log 'queue completed after retry'
            break
        }
        Start-Sleep -Seconds ([Math]::Max(5, $RetryDelaySeconds))
    }
} finally {
    if ($ownsMutex) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}
