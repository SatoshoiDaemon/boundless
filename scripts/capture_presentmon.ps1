[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunDirectory,

    [Parameter(Mandatory = $true)]
    [ValidateSet('menu', 'startup-transition', 'existing-world', 'stationary-loaded-chunks', 'exploration-generated', 'exploration-new-terrain')]
    [string]$Scenario,

    [Parameter(Mandatory = $true)]
    [string]$PresentMonPath,

    [int]$ProcessId = 0,

    [ValidateRange(10, 1800)]
    [int]$DurationSeconds = 120,

    [string]$ContextNote = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runPath = (Resolve-Path -LiteralPath $RunDirectory).Path
$presentMon = (Resolve-Path -LiteralPath $PresentMonPath).Path
$runInfoPath = Join-Path $runPath 'run.json'

if (-not (Test-Path -LiteralPath $runInfoPath -PathType Leaf)) {
    throw "Run metadata not found: $runInfoPath. Start the session with capture_perf_session.ps1 first."
}

$runInfo = Get-Content -LiteralPath $runInfoPath -Raw | ConvertFrom-Json
$expectedRunScenario = switch ($Scenario) {
    'menu' { 'client-startup' }
    'startup-transition' { 'client-startup' }
    'existing-world' { 'existing-world-entry' }
    default { $Scenario }
}
if ($runInfo.scenario -ne $expectedRunScenario) {
    throw "PresentMon scenario '$Scenario' does not match run.json scenario '$($runInfo.scenario)'."
}

if (-not (Test-Path -LiteralPath $presentMon -PathType Leaf)) {
    throw "PresentMon executable not found: $PresentMonPath"
}

if ($ProcessId -le 0) {
    $candidates = Get-CimInstance Win32_Process -Filter "Name='javaw.exe' OR Name='java.exe'" -ErrorAction SilentlyContinue
    $game = $candidates | Where-Object {
        $_.CommandLine -and $_.CommandLine.IndexOf($repoRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0
    } | Select-Object -First 1
    if (-not $game) { throw 'No Minecraft Java process with this instance path was found. Pass -ProcessId explicitly if needed.' }
    $ProcessId = [int]$game.ProcessId
}

$stamp = Get-Date -Format 'HHmmss'
$outputPath = Join-Path $runPath ("frametime-{0}-{1}.csv" -f $Scenario, $stamp)
$metadataPath = Join-Path $runPath ("frametime-{0}-{1}.json" -f $Scenario, $stamp)
$metadata = [ordered]@{
    scenario = $Scenario
    processId = $ProcessId
    startedAtLocal = (Get-Date).ToString('o')
    durationSeconds = $DurationSeconds
    contextNote = $ContextNote
    metrics = 'PresentMon 2.x; all per-frame data retained in CSV'
    csv = [IO.Path]::GetFileName($outputPath)
}
$metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $metadataPath -Encoding UTF8

Write-Host "Capturing $DurationSeconds seconds for PID $ProcessId. Keep the benchmark scene unchanged."
$arguments = @(
    '--process_id', [string]$ProcessId,
    '--output_file', $outputPath,
    '--timed', [string]$DurationSeconds,
    '--terminate_after_timed',
    '--v2_metrics',
    '--date_time'
)
& $presentMon @arguments
if ($LASTEXITCODE -ne 0) {
    throw "PresentMon exited with code $LASTEXITCODE. Keep the diagnostic output and rerun with an elevated terminal if ETW access was denied."
}

$csvRows = [math]::Max(0, (Get-Content -LiteralPath $outputPath).Count - 1)
if ($csvRows -eq 0) {
    throw "PresentMon returned no frame rows for PID $ProcessId. Keep the capture metadata and inspect the PresentMon output before treating it as an FPS sample."
}
$metadata.frameRowCount = $csvRows

$metadata.endedAtLocal = (Get-Date).ToString('o')
$metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $metadataPath -Encoding UTF8
Write-Host "Frame data saved to $outputPath"
