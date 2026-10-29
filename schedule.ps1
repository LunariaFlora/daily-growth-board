param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference='Stop'
$settings=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$taskName='Lunaria-Growth-Board-Reminder'
$shell="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$launcher=Join-Path $PSScriptRoot 'open.ps1'
$action=New-ScheduledTaskAction -Execute $shell -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$launcher+'"') -WorkingDirectory $PSScriptRoot
$user=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$taskSettings=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
$taskSettings.StartWhenAvailable=$false
$taskSettings.WakeToRun=$false
$triggers=@($settings.times | ForEach-Object {
    if ($_ -notmatch '^(?:[01]\d|2[0-3]):[0-5]\d$') { throw 'Invalid reminder time' }
    New-ScheduledTaskTrigger -Daily -At $_
})
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Principal $principal -Settings $taskSettings -Description 'Open the personal growth board at chosen times.' -Force | Out-Null
if (-not $settings.enabled) { Disable-ScheduledTask -TaskName $taskName | Out-Null }
