param([switch]$ForceRuntime)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$runtimeDir=Join-Path $projectRoot 'runtime'
if($ForceRuntime -or -not(Test-Path -LiteralPath (Join-Path $runtimeDir 'python.exe'))){
    $buildDir=Join-Path $projectRoot 'build'
    New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
    $archive=Join-Path $buildDir 'python-3.13.17-embed-amd64.zip'
    Invoke-WebRequest 'https://www.python.org/ftp/python/3.13.17/python-3.13.17-embed-amd64.zip' -OutFile $archive
    $expected='9E35319BFFEDAB8B36AD44D8F377CB4F1733BCEC257A0B6D04D94F01486DDB38'
    if((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expected){throw 'Python archive checksum mismatch.'}
    Expand-Archive -LiteralPath $archive -DestinationPath $runtimeDir -Force
}
[IO.File]::WriteAllText((Join-Path $runtimeDir 'python313._pth'),"python313.zip`n.`n..`n",[Text.UTF8Encoding]::new($false))
$compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if(-not(Test-Path -LiteralPath $compiler)){throw '.NET Framework C# compiler is required on Windows.'}
& $compiler /nologo /target:winexe /reference:System.Windows.Forms.dll ('/win32icon:'+(Join-Path $projectRoot 'public\icons\icon-05-light.ico')) ('/out:'+(Join-Path $projectRoot '日有所积.exe')) (Join-Path $projectRoot 'launcher.cs')
if($LASTEXITCODE -ne 0){throw 'Launcher compilation failed.'}
Write-Output 'Windows runtime and launcher are ready. No service or scheduled task was started.'
