param([switch]$Background)
$ErrorActionPreference = 'Stop'
$runtimePath = Join-Path $PSScriptRoot 'data\runtime.json'
$statePath = Join-Path $PSScriptRoot 'data\state.json'
if (Test-Path -LiteralPath $runtimePath) {
    $runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
    $process = Get-CimInstance Win32_Process -Filter ('ProcessId=' + [int]$runtime.pid)
    if ($process) {
        $expected = Join-Path $PSScriptRoot 'server.py'
        if ($process.CommandLine -notlike ('*"' + $expected + '"*')) { throw 'The running process does not match this board. No process was stopped.' }
        $url = 'http://127.0.0.1:' + [int]$runtime.port
        $health = Invoke-RestMethod -Uri ($url + '/api/health') -TimeoutSec 3
        if ($health.app -ne 'lunaria-growth-board-v1') { throw 'Local application identity mismatch.' }
        for ($attempt=0; $attempt -lt 15; $attempt++) {
            $state = Invoke-RestMethod -Uri ($url + '/api/state') -TimeoutSec 3
            if (-not $state.pending) { break }
            Start-Sleep -Seconds 3
        }
        if ($state.pending) { throw 'Diary sync is still pending. Please resolve the sync issue in settings before updating.' }
        if (Test-Path -LiteralPath $statePath) {
            Copy-Item -LiteralPath $statePath -Destination (Join-Path $PSScriptRoot ('data\before-update-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json'))
        }
        Stop-Process -Id ([int]$runtime.pid)
        Wait-Process -Id ([int]$runtime.pid) -ErrorAction SilentlyContinue
    }
}
& (Join-Path $PSScriptRoot 'open.ps1') -Background:$Background
