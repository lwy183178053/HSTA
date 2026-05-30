[CmdletBinding()]
param(
    [string]$WindowsPython = 'D:\ProgramData\anaconda3\envs\mybase\python.exe',
    [string]$PreferredWslDistro = 'Ubuntu-22.04',
    [switch]$SetDefaultWsl
)

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title =="
}

function Convert-ToWslPath {
    param([string]$Path)
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if ($resolved -notmatch '^([A-Za-z]):\\(.*)$') {
        throw "Only drive-letter Windows paths are supported: $resolved"
    }
    $drive = $matches[1].ToLowerInvariant()
    $tail = $matches[2] -replace '\\', '/'
    return "/mnt/$drive/$tail"
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$wslRepoRoot = Convert-ToWslPath $repoRoot

Write-Section "Repository"
Write-Host "Windows path: $repoRoot"
Write-Host "WSL path:     $wslRepoRoot"

Write-Section "Windows Python"
$barePython = Get-Command python -ErrorAction SilentlyContinue
if ($barePython) {
    Write-Host "bare python:  $($barePython.Source)"
} else {
    Write-Host "bare python:  not found"
}
if ($barePython -and $barePython.Source -like '*\Microsoft\WindowsApps\python.exe') {
    Write-Warning "Bare python is the Microsoft Store launcher stub. Use the Anaconda interpreter below."
}
if (Test-Path -LiteralPath $WindowsPython) {
    Write-Host "project py:   $WindowsPython"
    & $WindowsPython -c "import sys; print('version:     ' + sys.version.replace('\n', ' ')); print('executable:  ' + sys.executable)"
} else {
    Write-Warning "Project Anaconda interpreter not found: $WindowsPython"
}

Write-Section "WSL"
$wslList = (& wsl -l -v 2>$null) -join "`n"
Write-Host ($wslList -replace "`0", "")
if ($SetDefaultWsl) {
    Write-Host "Setting default WSL distro to $PreferredWslDistro"
    & wsl --set-default $PreferredWslDistro 2>$null
}

$distros = @('Ubuntu-22.04', 'traffic-ubuntu-22.04', 'docker-desktop')
foreach ($distro in $distros) {
    Write-Section "WSL Distro: $distro"
    & wsl -d $distro -- printenv WSL_DISTRO_NAME 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Cannot start distro: $distro"
        continue
    }

    & wsl -d $distro -- test -d $wslRepoRoot 2>$null
    Write-Host ("project path: " + ($(if ($LASTEXITCODE -eq 0) { "ok" } else { "missing" })))

    & wsl -d $distro -- test -x /bin/bash 2>$null
    Write-Host ("bash:         " + ($(if ($LASTEXITCODE -eq 0) { "ok" } else { "missing" })))

    & wsl -d $distro -- test -x /opt/traffic-mamba-venv/bin/python 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "mamba venv:   ok"
        & wsl -d $distro -- /opt/traffic-mamba-venv/bin/python --version 2>$null
    } else {
        Write-Host "mamba venv:   missing"
    }
}

Write-Section "Preferred WSL ML Stack"
& wsl -d $PreferredWslDistro -- /opt/traffic-mamba-venv/bin/python -c "import sys; print('python', sys.version.split()[0]); import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available()); import mamba_ssm; print('mamba_ssm ok')" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Preferred WSL ML stack check failed for $PreferredWslDistro"
}

Write-Section "Recommended Commands"
Write-Host "Windows Python:"
Write-Host "& '$WindowsPython' run_experiments.py --config configs\tls40_s.yaml --resume"
Write-Host ""
Write-Host "WSL Mamba/CUDA:"
Write-Host "wsl -d $PreferredWslDistro -- bash -lc `"cd $wslRepoRoot && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/tls40_s.yaml --resume`""
