$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'open.ps1') -Background
$state=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data\state.json') -Raw | ConvertFrom-Json
$config=Join-Path $PSScriptRoot 'data\schedule-request.json'
$state.settings | ConvertTo-Json | Set-Content -LiteralPath $config -Encoding UTF8
& (Join-Path $PSScriptRoot 'schedule.ps1') -Config $config
$shell="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$launcher=Join-Path $PSScriptRoot 'open.ps1'
$user=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action=New-ScheduledTaskAction -Execute $shell -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$launcher+'" -Background') -WorkingDirectory $PSScriptRoot
$settings=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName 'Lunaria-Growth-Board-Startup' -Action $action -Trigger (New-ScheduledTaskTrigger -AtLogOn -User $user) -Principal (New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited) -Settings $settings -Force | Out-Null
# Create the user-facing shortcut after task registration succeeds.
$shortcut=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $PSScriptRoot '日有所积.lnk'))
$shortcut.TargetPath=$shell
$shortcut.Arguments='-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot 'bootstrap.ps1')+'"'
$shortcut.WorkingDirectory=$PSScriptRoot
$shortcut.Description='日有所积'
$selectedIcon=if($state.settings.appIcon){$state.settings.appIcon}else{'01'}
$iconFile=if($selectedIcon -eq '05'){'icon-05-light.ico'}else{'icon-'+$selectedIcon+'.ico'}
$shortcut.IconLocation=(Join-Path $PSScriptRoot ('public\icons\'+$iconFile))+',0'
$shortcut.Save()
Get-ScheduledTask -TaskName 'Lunaria-Growth-Board-*' | Select-Object TaskName,State
