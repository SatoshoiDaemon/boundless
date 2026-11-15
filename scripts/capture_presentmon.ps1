[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunDirectory,

    [Parameter(Mandatory = $true)]
    [ValidateSet('menu', 'startup-transition', 'existing-world', 'stationary-loaded-chunks', 'exploration-generated', 'exploration-new-terrain', 'shader-on-comparison', 'shader-off-comparison')]
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
    { $_ -in 'existing-world', 'stationary-loaded-chunks', 'exploration-generated', 'exploration-new-terrain', 'shader-on-comparison', 'shader-off-comparison' } { 'existing-world-entry' }
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
    metrics = 'PresentMon native per-frame CSV; all rows retained'
    csv = [IO.Path]::GetFileName($outputPath)
}
$metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $metadataPath -Encoding UTF8

Write-Host "Capturing $DurationSeconds seconds for PID $ProcessId. Keep the benchmark scene unchanged."
$metadata.startedAtLocal = (Get-Date).ToString('o')
$metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $metadataPath -Encoding UTF8
$arguments = @(
    '-process_id', [string]$ProcessId,
    '-output_file', $outputPath,
    '-timed', [string]$DurationSeconds,
    '-terminate_after_timed'
)
# PresentMon writes one row per frame to stdout as well as to the CSV. Drain
# stdout so a five-minute capture does not flood the operator console; keep
# stderr visible for ETW and capture diagnostics, and preserve LASTEXITCODE.
& $presentMon @arguments 1>$null
$metadata.endedAtLocal = (Get-Date).ToString('o')
if ($LASTEXITCODE -ne 0) {
    throw "PresentMon exited with code $LASTEXITCODE. Keep the diagnostic output and rerun with an elevated terminal if ETW access was denied."
}

$lineCount = 0
$reader = [System.IO.StreamReader]::new($outputPath)
try {
    while ($null -ne $reader.ReadLine()) { $lineCount++ }
}
finally {
    $reader.Dispose()
}
$csvRows = [math]::Max(0, $lineCount - 1)
if ($csvRows -eq 0) {
    throw "PresentMon returned no frame rows for PID $ProcessId. Keep the capture metadata and inspect the PresentMon output before treating it as an FPS sample."
}
$metadata.frameRowCount = $csvRows

$metadata.postProcessingEndedAtLocal = (Get-Date).ToString('o')
$metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $metadataPath -Encoding UTF8
Write-Host "Frame data saved to $outputPath"
