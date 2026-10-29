param([switch]$Background)
$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot 'data\runtime.json'
function Get-BoardUrl {
    if (Test-Path -LiteralPath $runtime) {
        try {
            $r = Get-Content -LiteralPath $runtime -Raw | ConvertFrom-Json
            $url = 'http://127.0.0.1:' + [int]$r.port
            $health = Invoke-RestMethod -Uri ($url + '/api/health') -TimeoutSec 2
            if ($health.app -eq 'lunaria-growth-board-v1') { return $url }
        } catch {}
    }
    return $null
}
$url = Get-BoardUrl
if (-not $url) {
    $python = Join-Path $PSScriptRoot 'runtime\pythonw.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        $python = (Get-Command pythonw.exe -ErrorAction Stop).Source
    }
    Start-Process -FilePath $python -ArgumentList ('"' + (Join-Path $PSScriptRoot 'server.py') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
    for ($i=0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 400
        $url = Get-BoardUrl
        if ($url) { break }
    }
}
if (-not $url) { throw 'The local board could not be started. See data/server-error.log.' }
if (-not $Background) {
    $chrome = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe", "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($chrome) {
        # A board-only profile keeps the user's normal Chrome theme untouched.
        $state = Invoke-RestMethod -Uri ($url + '/api/state') -TimeoutSec 3
        $chosenIcon=if($state.settings.appIcon){$state.settings.appIcon}else{'01'}
        foreach($name in @('日有所积.lnk','成长看板.lnk')) {
            if($name -eq '日有所积.lnk' -or (Test-Path -LiteralPath (Join-Path $PSScriptRoot $name))) {
                $shortcut=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $PSScriptRoot $name))
                $shortcut.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
                $shortcut.Arguments='-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot 'bootstrap.ps1')+'"'
                $shortcut.WorkingDirectory=$PSScriptRoot
                $shortcut.IconLocation=(Join-Path $PSScriptRoot ('public\icons\icon-'+$chosenIcon+$(if($chosenIcon -eq '05'){'-light.ico'}else{'.ico'})))+',0'
                $shortcut.Save()
            }
        }
        $tone = if ($state.settings.style -eq '03') { 'dark' } else { 'light' }
        $profile = Join-Path $PSScriptRoot ('data\browser-' + $tone)
        $preferences = Join-Path $profile 'Default\Preferences'
        if (-not (Test-Path -LiteralPath $preferences)) {
            New-Item -ItemType Directory -Path (Split-Path $preferences) -Force | Out-Null
            # Chromium ThemeService::BrowserColorScheme: light=1, dark=2.
            # Seed only a new board profile; never overwrite a running profile.
            $scheme = if ($tone -eq 'dark') { 2 } else { 1 }
            $prefs = @{browser=@{theme=@{color_scheme=$scheme; color_scheme2=$scheme; follows_system_colors=$false}}}
            [IO.File]::WriteAllText($preferences, ($prefs | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
        }
        Start-Process -FilePath $chrome -ArgumentList @("--app=$url", '--start-maximized', ('--user-data-dir="' + $profile + '"'), '--no-first-run', '--no-default-browser-check')
    }
    else { Start-Process $url }
}
