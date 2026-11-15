[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'client-startup',
        'existing-world-entry',
        'stationary-loaded-chunks',
        'exploration-generated',
        'exploration-new-terrain'
    )]
    [string]$Scenario,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$')]
    [string]$RunId,

    [string]$WorldLabel = '',
    [string]$Seed = '',
    [string]$Route = '',
    [string]$VisualProfile = '',

    [ValidateRange(1, 720)]
    [int]$DurationMinutes = 90,

    [ValidateRange(1, 30)]
    [int]$SampleIntervalSeconds = 2,

    [switch]$ProfileJfr,

    [ValidateRange(1, 180)]
    [int]$JfrDurationMinutes = 45
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$captureStart = Get-Date
$runDate = $captureStart.ToString('yyyy-MM-dd')
$runDirectory = Join-Path (Join-Path (Join-Path $repoRoot 'auditoria/testes/runs') $runDate) $RunId
$logPath = Join-Path $repoRoot 'logs/latest.log'

if (Test-Path -LiteralPath $runDirectory) {
    throw "Capture directory already exists: $runDirectory"
}

New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null

function Get-GitValue([string[]]$GitArguments) {
    $value = & git -C $repoRoot @GitArguments 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return (($value | Out-String).Trim())
}

function Get-OptionValue([string]$Path, [string]$Key) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $escapedKey = [regex]::Escape($Key)
    $line = Get-Content -LiteralPath $Path | Where-Object { $_ -match "^${escapedKey}:(.*)$" } | Select-Object -First 1
    if ($line -and $line -match "^${escapedKey}:(.*)$") { return $Matches[1] }
    return $null
}

function Get-PropertyValue([string]$Path, [string]$Key) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $escapedKey = [regex]::Escape($Key)
    $line = Get-Content -LiteralPath $Path | Where-Object { $_ -match "^\s*${escapedKey}\s*=(.*)$" } | Select-Object -First 1
    if ($line -and $line -match "^\s*${escapedKey}\s*=(.*)$") { return $Matches[1].Trim() }
    return $null
}

function Get-RelativePathCompat([string]$BasePath, [string]$TargetPath) {
    $base = (Resolve-Path -LiteralPath $BasePath).Path.TrimEnd('\', '/')
    $target = (Resolve-Path -LiteralPath $TargetPath).Path
    $prefix = $base + [IO.Path]::DirectorySeparatorChar
    if ($target.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        return $target.Substring($prefix.Length).Replace('\', '/')
    }
    throw "Path '$TargetPath' is outside base path '$BasePath'."
}

function Get-Sha256Hex([string]$Path) {
    $stream = [IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).Path)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $algorithm.ComputeHash($stream)
    }
    finally {
        $algorithm.Dispose()
        $stream.Dispose()
    }
    return [BitConverter]::ToString($hashBytes).Replace('-', '').ToLowerInvariant()
}

function Get-ConfigFingerprints {
    $extensions = @('.toml', '.properties', '.json', '.cfg', '.txt')
    $configurationFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $repoRoot 'config') -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() } |
            Sort-Object FullName
    )
    foreach ($item in $configurationFiles) {
        [pscustomobject]@{
            file = Get-RelativePathCompat $repoRoot $item.FullName
            sizeBytes = $item.Length
            sha256 = Get-Sha256Hex $item.FullName
        }
    }

    $optionsPath = Join-Path $repoRoot 'options.txt'
    if (Test-Path -LiteralPath $optionsPath -PathType Leaf) {
        $item = Get-Item -LiteralPath $optionsPath
        [pscustomobject]@{
            file = 'options.txt'
            sizeBytes = $item.Length
        sha256 = Get-Sha256Hex $optionsPath
        }
    }
}

function Find-GameProcess {
    $candidates = Get-CimInstance Win32_Process -Filter "Name='javaw.exe' OR Name='java.exe'" -ErrorAction SilentlyContinue
    foreach ($candidate in $candidates) {
        $commandLine = [string]$candidate.CommandLine
        if ($commandLine -and $commandLine.IndexOf($repoRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
            return $candidate
        }
    }
    return $null
}

$jarFiles = @(Get-ChildItem -LiteralPath (Join-Path $repoRoot 'mods') -File -Filter '*.jar' | Sort-Object Name)
$modLockPath = Join-Path $runDirectory 'mod-lock.csv'
$jarFiles | ForEach-Object {
    [pscustomobject]@{
        file = $_.Name
        sizeBytes = $_.Length
        sha256 = Get-Sha256Hex $_.FullName
    }
} | Export-Csv -LiteralPath $modLockPath -NoTypeInformation -Encoding UTF8

$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$processors = @(Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name -Unique)
$graphics = @(Get-CimInstance Win32_VideoController | ForEach-Object {
    [pscustomobject]@{
        name = $_.Name
        driverVersion = $_.DriverVersion
        currentWidth = $_.CurrentHorizontalResolution
        currentHeight = $_.CurrentVerticalResolution
    }
})
$configFingerprints = @(Get-ConfigFingerprints)
$shaderConfig = Join-Path $repoRoot 'config/oculus.properties'
$optionsPath = Join-Path $repoRoot 'options.txt'
$profileJfrPath = Join-Path $runDirectory 'runtime-profile.jfr'
$gitCommit = Get-GitValue -GitArguments @('rev-parse', 'HEAD')
$gitBranch = Get-GitValue -GitArguments @('branch', '--show-current')
$gitStatus = Get-GitValue -GitArguments @('status', '--porcelain')
$workingTreeClean = [string]::IsNullOrWhiteSpace($gitStatus)

$runInfo = [ordered]@{
    schemaVersion = 1
    runId = $RunId
    scenario = $Scenario
    status = 'capturing'
    startedAtLocal = $captureStart.ToString('o')
    startedAtUtc = $captureStart.ToUniversalTime().ToString('o')
    endedAtLocal = $null
    endedAtUtc = $null
    stopReason = $null
    git = [ordered]@{ commit = $gitCommit; branch = $gitBranch; workingTreeClean = $workingTreeClean }
    minecraft = [ordered]@{ version = '1.20.1'; forge = '47.4.28'; javaMajor = 17 }
    world = [ordered]@{ label = $WorldLabel; seed = $Seed; route = $Route }
    visual = [ordered]@{
        profile = $VisualProfile
        renderDistance = Get-OptionValue $optionsPath 'renderDistance'
        simulationDistance = Get-OptionValue $optionsPath 'simulationDistance'
        graphicsMode = Get-OptionValue $optionsPath 'graphicsMode'
        fullscreen = Get-OptionValue $optionsPath 'fullscreen'
        shaderPack = Get-PropertyValue $shaderConfig 'shaderPack'
        shadersEnabled = Get-PropertyValue $shaderConfig 'enableShaders'
    }
    host = [ordered]@{
        os = $os.Caption
        osVersion = $os.Version
        processors = $processors
        logicalProcessors = $computer.NumberOfLogicalProcessors
        physicalMemoryBytes = [int64]$computer.TotalPhysicalMemory
        graphics = $graphics
        screenResolution = if ($graphics.Count -and $graphics[0].currentWidth -and $graphics[0].currentHeight) {
            "{0}x{1}" -f $graphics[0].currentWidth, $graphics[0].currentHeight
        } else {
            $null
        }
    }
    inventory = [ordered]@{
        modJarCount = $jarFiles.Count
        modLock = 'mod-lock.csv'
        configFingerprints = $configFingerprints
        selectedShaderPack = Get-PropertyValue $shaderConfig 'shaderPack'
        selectedShaderPackSha256 = $null
        selectedShaderPackFileCount = 0
    }
    capture = [ordered]@{
        sampleIntervalSeconds = $SampleIntervalSeconds
        maximumDurationMinutes = $DurationMinutes
        jfrProfileEnabled = [bool]$ProfileJfr
        jfrDurationMinutes = if ($ProfileJfr) { $JfrDurationMinutes } else { $null }
        jfrFile = if ($ProfileJfr) { 'runtime-profile.jfr' } else { $null }
        lastGameProcessId = $null
        javaExecutable = $null
        latestLogCopied = $false
    }
}

$selectedShaderPack = [string]$runInfo.inventory.selectedShaderPack
if (-not [string]::IsNullOrWhiteSpace($selectedShaderPack)) {
    $shaderPackPath = Join-Path (Join-Path $repoRoot 'shaderpacks') $selectedShaderPack
    if (Test-Path -LiteralPath $shaderPackPath -PathType Leaf) {
        $runInfo.inventory.selectedShaderPackSha256 = Get-Sha256Hex $shaderPackPath
        $runInfo.inventory.selectedShaderPackFileCount = 1
    } elseif (Test-Path -LiteralPath $shaderPackPath -PathType Container) {
        $shaderFiles = @(Get-ChildItem -LiteralPath $shaderPackPath -File -Recurse)
        $shaderFingerprints = [System.Collections.Generic.List[string]]::new()
        foreach ($item in $shaderFiles) {
            $relativePath = (Get-RelativePathCompat $shaderPackPath $item.FullName).ToLowerInvariant()
            $sha = Get-Sha256Hex $item.FullName
            $shaderFingerprints.Add("${relativePath}:$sha")
        }
        $shaderFingerprints.Sort([StringComparer]::Ordinal)
        $bytes = [Text.Encoding]::UTF8.GetBytes(($shaderFingerprints -join "`n"))
        $hashBytes = [Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
        $runInfo.inventory.selectedShaderPackSha256 = [BitConverter]::ToString($hashBytes).Replace('-', '').ToLowerInvariant()
        $runInfo.inventory.selectedShaderPackFileCount = $shaderFiles.Count
    }
}

function Save-RunInfo {
    $target = Join-Path $runDirectory 'run.json'
    $temporary = Join-Path $runDirectory 'run.json.tmp'
    $runInfo | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $target -Force
}

$samplesPath = Join-Path $runDirectory 'system-samples.csv'
$eventsPath = Join-Path $runDirectory 'events.csv'
$writer = New-Object System.IO.StreamWriter($samplesPath, $false, (New-Object System.Text.UTF8Encoding($false)))
$writer.WriteLine('timestamp_utc,elapsed_s,pid,process_cpu_s,process_cpu_pct,working_set_bytes,private_bytes,total_cpu_pct,free_physical_bytes,process_page_faults_per_sec,commit_pct,pages_per_sec,page_reads_per_sec,pages_input_per_sec,pages_output_per_sec')
$writer.Flush()
Set-Content -LiteralPath $eventsPath -Value 'timestamp_utc,timestamp_local,event,scenario,elapsed_s,note' -Encoding UTF8
Save-RunInfo

Write-Host "Run metadata and JAR lock saved under auditoria/testes/runs/$runDate/$RunId"
Write-Host 'Launch Minecraft from CurseForge. Press Enter here to stop the capture.'
if ($ProfileJfr) { Write-Host "JFR profile will attach to the Minecraft JVM when it appears; file: $($runInfo.capture.jfrFile)" }

$previousCpuSeconds = $null
$previousSampleAt = $null
$firstProcessAt = $null
$lastProcessAt = $null
$trackedProcessId = $null
$jfrStarted = $false
$stopReason = 'duration-limit'
$lastMetadataSave = Get-Date
$captureDeadline = $captureStart.AddMinutes($DurationMinutes)
$systemCpuCounterAvailable = $true

try {
    while ((Get-Date) -lt $captureDeadline) {
        $now = Get-Date
        $game = Find-GameProcess
        $processId = $null
        $cpuSeconds = $null
        $workingSet = $null
        $privateBytes = $null
        $processCpuPct = $null

        if ($game) {
            $processId = [int]$game.ProcessId
            $lastProcessAt = $now
            if ($trackedProcessId -ne $processId) {
                $previousCpuSeconds = $null
                $previousSampleAt = $null
                $trackedProcessId = $processId
            }
            if (-not $firstProcessAt) {
                $firstProcessAt = $now
                $runInfo.capture.lastGameProcessId = $processId
                $runInfo.capture.javaExecutable = $game.ExecutablePath
            }

            $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($process) {
                $cpuSeconds = [double]$process.CPU
                $workingSet = [int64]$process.WorkingSet64
                $privateBytes = [int64]$process.PrivateMemorySize64
                if ($null -ne $previousCpuSeconds -and $null -ne $previousSampleAt) {
                    $sampleElapsed = ($now - $previousSampleAt).TotalSeconds
                    if ($sampleElapsed -gt 0) {
                        $logicalCount = [math]::Max(1, [int]$computer.NumberOfLogicalProcessors)
                        $processCpuPct = 100.0 * ($cpuSeconds - $previousCpuSeconds) / ($sampleElapsed * $logicalCount)
                    }
                }
                $previousCpuSeconds = $cpuSeconds
                $previousSampleAt = $now
            }

            if ($ProfileJfr -and -not $jfrStarted -and $game.ExecutablePath) {
                $jcmdPath = Join-Path (Split-Path -Parent $game.ExecutablePath) 'jcmd.exe'
                if (Test-Path -LiteralPath $jcmdPath) {
                    $jfrName = ('BoundlessP01_' + ($RunId -replace '[^A-Za-z0-9_]', '_'))
                    $jfrArgs = @(
                        [string]$processId,
                        'JFR.start',
                        "name=$jfrName",
                        'settings=profile',
                        "duration=$($JfrDurationMinutes * 60)s",
                        "filename=$profileJfrPath",
                        'maxsize=512m'
                    )
                    & $jcmdPath @jfrArgs 2>&1 | Out-Null
                    if ($LASTEXITCODE -eq 0) { $jfrStarted = $true }
                }
            }
        }

        $totalCpuPct = $null
        if ($systemCpuCounterAvailable) {
            try {
                $cpuCounter = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'" -ErrorAction Stop
                $totalCpuPct = [double]$cpuCounter.PercentProcessorTime
            } catch {
                $systemCpuCounterAvailable = $false
            }
        }

        $memorySnapshot = Get-CimInstance Win32_OperatingSystem -Property FreePhysicalMemory -ErrorAction SilentlyContinue
        $freePhysicalBytes = if ($memorySnapshot) { [int64]$memorySnapshot.FreePhysicalMemory * 1024 } else { $null }
        $memoryCounters = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory -ErrorAction SilentlyContinue
        $processCounters = if ($null -ne $processId) {
            Get-CimInstance Win32_PerfFormattedData_PerfProc_Process -Filter "IDProcess=$processId" -ErrorAction SilentlyContinue
        } else {
            $null
        }
        $elapsed = ($now - $captureStart).TotalSeconds
        $format = [System.Globalization.CultureInfo]::InvariantCulture
        $values = @(
            $now.ToUniversalTime().ToString('o'),
            $elapsed.ToString('F3', $format),
            $(if ($null -ne $processId) { [string]$processId } else { '' }),
            $(if ($null -ne $cpuSeconds) { $cpuSeconds.ToString('F3', $format) } else { '' }),
            $(if ($null -ne $processCpuPct) { $processCpuPct.ToString('F2', $format) } else { '' }),
            $(if ($null -ne $workingSet) { [string]$workingSet } else { '' }),
            $(if ($null -ne $privateBytes) { [string]$privateBytes } else { '' }),
            $(if ($null -ne $totalCpuPct) { $totalCpuPct.ToString('F2', $format) } else { '' }),
            $(if ($null -ne $freePhysicalBytes) { [string]$freePhysicalBytes } else { '' }),
            $(if ($processCounters) { [string]$processCounters.PageFaultsPersec } else { '' }),
            $(if ($memoryCounters) { [string]$memoryCounters.PercentCommittedBytesInUse } else { '' }),
            $(if ($memoryCounters) { [string]$memoryCounters.PagesPersec } else { '' }),
            $(if ($memoryCounters) { [string]$memoryCounters.PageReadsPersec } else { '' }),
            $(if ($memoryCounters) { [string]$memoryCounters.PagesInputPersec } else { '' }),
            $(if ($memoryCounters) { [string]$memoryCounters.PagesOutputPersec } else { '' })
        )
        $writer.WriteLine(($values -join ','))
        $writer.Flush()

        if (($now - $lastMetadataSave).TotalSeconds -ge 30) {
            Save-RunInfo
            $lastMetadataSave = $now
        }

        if ($firstProcessAt -and -not $game -and $lastProcessAt -and ($now - $lastProcessAt).TotalSeconds -ge 45) {
            $stopReason = 'game-process-exited'
            break
        }

        try {
            if ([Console]::KeyAvailable) {
                $key = [Console]::ReadKey($true)
                if ($key.Key -eq [ConsoleKey]::Enter) {
                    $stopReason = 'manual-stop'
                    break
                }
            }
        } catch {
            # Non-interactive consoles use the duration limit or process-exit stop condition.
        }

        Start-Sleep -Seconds $SampleIntervalSeconds
    }
} finally {
    $writer.Flush()
    $writer.Dispose()
    $end = Get-Date
    $runInfo.status = if ($stopReason -eq 'duration-limit') { 'duration-complete' } else { 'complete' }
    $runInfo.endedAtLocal = $end.ToString('o')
    $runInfo.endedAtUtc = $end.ToUniversalTime().ToString('o')
    $runInfo.stopReason = $stopReason
    if ($trackedProcessId) { $runInfo.capture.lastGameProcessId = $trackedProcessId }
    if ($ProfileJfr) { $runInfo.capture.jfrStarted = $jfrStarted }

    if (Test-Path -LiteralPath $logPath) {
        try {
            Copy-Item -LiteralPath $logPath -Destination (Join-Path $runDirectory 'latest.log') -Force
            $runInfo.capture.latestLogCopied = $true
        } catch {
            $runInfo.capture.latestLogCopied = $false
        }
    }

    Save-RunInfo
}

Write-Host "Capture stopped ($stopReason). Run data: $runDirectory"
