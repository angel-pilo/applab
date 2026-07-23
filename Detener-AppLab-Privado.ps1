$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$tailscale = "C:\Program Files\Tailscale\tailscale.exe"
$pidFile = Join-Path $projectRoot ".runtime\applab.pid"
$cloudflaredPidFile = Join-Path $projectRoot ".runtime\cloudflared.pid"

if (Test-Path -LiteralPath $cloudflaredPidFile) {
    $cloudflaredPid = Get-Content -LiteralPath $cloudflaredPidFile -ErrorAction SilentlyContinue
    if ($cloudflaredPid) {
        Stop-Process -Id $cloudflaredPid -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $cloudflaredPidFile -Force
}

if (Test-Path -LiteralPath $tailscale) {
    & $tailscale serve reset
}

if (Test-Path -LiteralPath $pidFile) {
    $savedPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue
    if ($savedPid) {
        Stop-Process -Id $savedPid -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $pidFile -Force
}

Write-Host "AppLab se detuvo."
