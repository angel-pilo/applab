$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $projectRoot ".runtime"
$cloudflared = Join-Path $runtimeDir "cloudflared.exe"
$pidFile = Join-Path $runtimeDir "cloudflared.pid"
$stdoutLog = Join-Path $runtimeDir "cloudflared.out.log"
$stderrLog = Join-Path $runtimeDir "cloudflared.err.log"

if (-not (Test-Path -LiteralPath $cloudflared)) {
    throw "No se encontro cloudflared. Vuelve a solicitar a Codex que prepare el enlace temporal."
}

try {
    $health = Invoke-RestMethod "http://127.0.0.1:5000/health" -TimeoutSec 3
}
catch {
    throw "AppLab no esta iniciado. Ejecuta primero Iniciar-AppLab-Privado.cmd."
}
if ($health.status -ne "ok") {
    throw "El healthcheck de AppLab no respondio correctamente."
}

$tunnelIsRunning = $false
if (Test-Path -LiteralPath $pidFile) {
    $savedPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue
    if ($savedPid) {
        $tunnelIsRunning = $null -ne (Get-Process -Id $savedPid -ErrorAction SilentlyContinue)
    }
}

if (-not $tunnelIsRunning) {
    Remove-Item -LiteralPath $stdoutLog -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $stderrLog -Force -ErrorAction SilentlyContinue
    $tunnel = Start-Process `
        -FilePath $cloudflared `
        -ArgumentList @("tunnel", "--url", "http://127.0.0.1:5000", "--no-autoupdate") `
        -WorkingDirectory $projectRoot `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -WindowStyle Hidden `
        -PassThru
    Set-Content -LiteralPath $pidFile -Value $tunnel.Id
}

$publicUrl = $null
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    $log = Get-Content -LiteralPath $stderrLog -Raw -ErrorAction SilentlyContinue
    $match = [regex]::Match($log, "https://[a-z0-9-]+\.trycloudflare\.com")
    if ($match.Success) {
        $publicUrl = $match.Value
        break
    }
    Start-Sleep -Milliseconds 500
}

if (-not $publicUrl) {
    throw "No se pudo obtener el enlace temporal. Revisa $stderrLog"
}

Write-Host ""
Write-Host "Enlace publico temporal:"
Write-Host $publicUrl
Write-Host ""
Write-Host "Cuando termines, ejecuta Volver-AppLab-Privado.cmd."
