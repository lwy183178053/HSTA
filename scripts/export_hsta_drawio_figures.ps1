param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$DrawioExe = 'C:\Program Files\draw.io\draw.io.exe'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $DrawioExe)) {
    throw "draw.io CLI not found: $DrawioExe"
}

$outputDir = Join-Path $ProjectRoot 'paper\figures_drawio'
$source = Join-Path $outputDir 'JNCA_HSTA_Figures.drawio'
if (-not (Test-Path -LiteralPath $source)) {
    throw "draw.io source not found: $source"
}

$files = @(
    'fig1_hsta_architecture.png',
    'fig2_main_macro_f1.png',
    'fig3_attention_position_ablation.png',
    'fig4_parameter_performance.png',
    'fig5_cross_protocol_transfer.png',
    'fig6_confusion_patterns.png',
    'fig7_data_processing_pipeline.png'
)

for ($index = 0; $index -lt $files.Count; $index++) {
    $target = Join-Path $outputDir $files[$index]
    $pageIndex = $index + 1
    $profile = Join-Path $env:TEMP ("drawio-hsta-{0}-{1}" -f $PID, $index)
    New-Item -ItemType Directory -Path $profile -Force | Out-Null
    $arguments = @(
        "--user-data-dir=$profile",
        '--disable-gpu',
        '--export',
        '--format', 'png',
        '--page-index', [string]$pageIndex,
        '--width', '2400',
        '--border', '20',
        '--output', $target,
        $source
    )
    $process = Start-Process -FilePath $DrawioExe -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        throw "draw.io export failed for page $index with exit code $($process.ExitCode)"
    }
    $item = Get-Item -LiteralPath $target -ErrorAction Stop
    if ($item.Length -le 0) {
        throw "draw.io export produced an empty file: $target"
    }
    Write-Output ("Exported page {0}: {1} ({2} bytes)" -f $index, $target, $item.Length)
}

$graphicalSource = Join-Path $outputDir 'JNCA_HSTA_Graphical_Abstract.drawio'
$graphicalTarget = Join-Path $outputDir 'graphical_abstract_hsta.png'
if (-not (Test-Path -LiteralPath $graphicalSource)) {
    throw "Graphical abstract source not found: $graphicalSource"
}
$graphicalProfile = Join-Path $env:TEMP ("drawio-hsta-{0}-graphical" -f $PID)
New-Item -ItemType Directory -Path $graphicalProfile -Force | Out-Null
$graphicalArguments = @(
    "--user-data-dir=$graphicalProfile",
    '--disable-gpu',
    '--export',
    '--format', 'png',
    '--page-index', '1',
    '--width', '3000',
    '--border', '20',
    '--output', $graphicalTarget,
    $graphicalSource
)
$graphicalProcess = Start-Process -FilePath $DrawioExe -ArgumentList $graphicalArguments -Wait -PassThru -WindowStyle Hidden
if ($graphicalProcess.ExitCode -ne 0) {
    throw "draw.io export failed for the graphical abstract with exit code $($graphicalProcess.ExitCode)"
}
$graphicalItem = Get-Item -LiteralPath $graphicalTarget -ErrorAction Stop
if ($graphicalItem.Length -le 0) {
    throw "draw.io export produced an empty graphical abstract: $graphicalTarget"
}
Write-Output ("Exported graphical abstract: {0} ({1} bytes)" -f $graphicalTarget, $graphicalItem.Length)
