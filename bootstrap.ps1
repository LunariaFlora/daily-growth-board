$ErrorActionPreference='Stop'
try {
    $runtimePath=Join-Path $PSScriptRoot 'data\runtime.json'
    if(Test-Path -LiteralPath $runtimePath) {
        $old=$null
        try {
            $r=Get-Content -LiteralPath $runtimePath -Raw|ConvertFrom-Json
            $old=Invoke-RestMethod -Uri ('http://127.0.0.1:'+$r.port+'/api/health') -TimeoutSec 2
        } catch {}
        if($old -and $old.app -eq 'lunaria-growth-board-v1' -and $old.version -ne 6) {
            & (Join-Path $PSScriptRoot 'restart.ps1') -Background
        }
    }
    $marker=Join-Path $PSScriptRoot 'data\installed-path.txt'
    if (-not (Test-Path -LiteralPath $marker) -or (Get-Content -LiteralPath $marker -Raw).Trim() -ne $PSScriptRoot) {
        try {
            & (Join-Path $PSScriptRoot 'install.ps1') | Out-Null
            [IO.File]::WriteAllText($marker,$PSScriptRoot,[Text.UTF8Encoding]::new($false))
        } catch {
            New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot 'data') -Force | Out-Null
            $_.Exception.Message | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'data\setup-warning.log')
        }
    }
    & (Join-Path $PSScriptRoot 'open.ps1')
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'日有所积 · 启动失败') | Out-Null
}
