$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $projectRoot ".runtime\cloudflared.pid"
$tailscale = "C:\Program Files\Tailscale\tailscale.exe"

if (Test-Path -LiteralPath $pidFile) {
    $savedPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue
    if ($savedPid) {
        Stop-Process -Id $savedPid -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $pidFile -Force
}

if (Test-Path -LiteralPath $tailscale) {
    & $tailscale serve --bg --yes http://127.0.0.1:5000
}

Write-Host "El enlace publico se desactivo. AppLab volvio a ser privado."
