[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunDirectory,

    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'menu-ready',
        'world-ready',
        'stationary-start',
        'stationary-end',
        'generated-route-start',
        'generated-route-end',
        'new-terrain-start',
        'new-terrain-end',
        'spark-sample',
        'tick-sample',
        'f3-sample'
    )]
    [string]$Event,

    [string]$Note = '',

    [double]$MeanTps = 0,
    [double]$AverageMspt = 0,
    [double]$P50Mspt = 0,
    [double]$P95Mspt = 0,
    [double]$P99Mspt = 0,
    [double]$MaxMspt = 0,
    [double]$Fps = 0,
    [double]$Fps1Low = 0,
    [double]$Fps01Low = 0,
    [double]$HeapUsedMiB = 0,
    [double]$HeapMaxMiB = 0,
    [double]$ServerTickMs = 0,
    [int]$RenderDistance = 0,
    [int]$SimulationDistance = 0,
    [int]$LoadedClientChunks = 0,
    [int]$LoadedServerChunks = 0,
    [int]$SpawnChunks = 0,
    [int]$TotalEntities = 0,
    [int]$Monsters = 0,
    [double]$GpuUtilizationPct = 0,
    [double]$AllocationRateMiBPerSecond = 0,
    [string]$Shaderpack = ''
)

$ErrorActionPreference = 'Stop'
$runPath = (Resolve-Path -LiteralPath $RunDirectory).Path
$runInfoPath = Join-Path $runPath 'run.json'
if (-not (Test-Path -LiteralPath $runInfoPath)) { throw "run.json not found under $runPath" }
$runInfo = Get-Content -LiteralPath $runInfoPath -Raw | ConvertFrom-Json
$now = Get-Date
$elapsedSeconds = $null
if ($runInfo.startedAtUtc) {
    $startUtc = [DateTimeOffset]::Parse([string]$runInfo.startedAtUtc).UtcDateTime
    $elapsedSeconds = ($now.ToUniversalTime() - $startUtc).TotalSeconds
}

$eventsPath = Join-Path $runPath 'events.csv'
if (-not (Test-Path -LiteralPath $eventsPath)) {
    Set-Content -LiteralPath $eventsPath -Value 'timestamp_utc,timestamp_local,event,scenario,elapsed_s,note' -Encoding UTF8
}
$escapedNote = $Note.Replace('"', '""').Replace("`r", ' ').Replace("`n", ' ')
$elapsedText = if ($null -ne $elapsedSeconds) { $elapsedSeconds.ToString('F3', [Globalization.CultureInfo]::InvariantCulture) } else { '' }
$eventRow = '"{0}","{1}","{2}","{3}",{4},"{5}"' -f `
    $now.ToUniversalTime().ToString('o'), $now.ToString('o'), $Event, $runInfo.scenario, $elapsedText, $escapedNote
Add-Content -LiteralPath $eventsPath -Value $eventRow -Encoding UTF8

if ($Event -eq 'spark-sample' -or $Event -eq 'tick-sample') {
    $sampleName = if ($Event -eq 'spark-sample') { 'spark-samples.csv' } else { 'tick-samples.csv' }
    $samplePath = Join-Path $runPath $sampleName
    if (-not (Test-Path -LiteralPath $samplePath)) {
        Set-Content -LiteralPath $samplePath -Value 'timestamp_utc,scenario,tps_kind,mean_tps,average_mspt,p50_mspt,p95_mspt,p99_mspt,max_mspt,fps,fps_1_percent_low,fps_0_1_percent_low,heap_used_mib,heap_max_mib,note' -Encoding UTF8
    }
    $tpsKind = if ($Event -eq 'spark-sample') { 'spark-rolling-measured' } else { 'mean-tick-time-equivalent' }
    $values = @(
        $now.ToUniversalTime().ToString('o'),
        $runInfo.scenario,
        $tpsKind,
        $MeanTps.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $AverageMspt.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $P50Mspt.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $P95Mspt.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $P99Mspt.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $MaxMspt.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $Fps.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $Fps1Low.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $Fps01Low.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $HeapUsedMiB.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $HeapMaxMiB.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        '"' + $escapedNote + '"'
    )
    Add-Content -LiteralPath $samplePath -Value ($values -join ',') -Encoding UTF8
}

if ($Event -eq 'f3-sample') {
    $f3Path = Join-Path $runPath 'manual-f3.csv'
    if (-not (Test-Path -LiteralPath $f3Path)) {
        Set-Content -LiteralPath $f3Path -Value 'timestamp_utc,scenario,fps,server_tick_ms,heap_used_mib,heap_max_mib,allocation_rate_mib_s,gpu_utilization_pct,render_distance,simulation_distance,loaded_client_chunks,loaded_server_chunks,spawn_chunks,total_entities,monsters,shaderpack,note' -Encoding UTF8
    }
    $csvValues = @(
        $now.ToUniversalTime().ToString('o'),
        $runInfo.scenario,
        $Fps.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $ServerTickMs.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $HeapUsedMiB.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $HeapMaxMiB.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $AllocationRateMiBPerSecond.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        $GpuUtilizationPct.ToString('F3', [Globalization.CultureInfo]::InvariantCulture),
        [string]$RenderDistance,
        [string]$SimulationDistance,
        [string]$LoadedClientChunks,
        [string]$LoadedServerChunks,
        [string]$SpawnChunks,
        [string]$TotalEntities,
        [string]$Monsters,
        '"' + $Shaderpack.Replace('"', '""') + '"',
        '"' + $escapedNote + '"'
    )
    Add-Content -LiteralPath $f3Path -Value ($csvValues -join ',') -Encoding UTF8
}

Write-Host ("Recorded {0} at {1}" -f $Event, $now.ToString('o'))
