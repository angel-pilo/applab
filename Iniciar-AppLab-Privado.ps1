$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$waitress = Join-Path $projectRoot "venv\Scripts\waitress-serve.exe"
$tailscale = "C:\Program Files\Tailscale\tailscale.exe"
$runtimeDir = Join-Path $projectRoot ".runtime"
$pidFile = Join-Path $runtimeDir "applab.pid"
$stdoutLog = Join-Path $runtimeDir "applab.out.log"
$stderrLog = Join-Path $runtimeDir "applab.err.log"

if (-not (Test-Path -LiteralPath $waitress)) {
    throw "No se encontro Waitress. Ejecuta: .\venv\Scripts\python.exe -m pip install waitress==3.0.2"
}
if (-not (Test-Path -LiteralPath $tailscale)) {
    throw "No se encontro Tailscale en C:\Program Files\Tailscale."
}

$tailscaleStatus = & $tailscale status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host $tailscaleStatus
    throw "Primero inicia sesion en Tailscale."
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

$appIsRunning = $false
if (Test-Path -LiteralPath $pidFile) {
    $savedPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue
    if ($savedPid) {
        $appIsRunning = $null -ne (Get-Process -Id $savedPid -ErrorAction SilentlyContinue)
    }
}

if (-not $appIsRunning) {
    $env:APP_PUBLIC_HTTPS = "1"
    $process = Start-Process `
        -FilePath $waitress `
        -ArgumentList @("--host=127.0.0.1", "--port=5000", "--call", "app:create_app") `
        -WorkingDirectory $projectRoot `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -WindowStyle Hidden `
        -PassThru
    Set-Content -LiteralPath $pidFile -Value $process.Id
}

$healthy = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" -TimeoutSec 2
        if ($health.status -eq "ok") {
            $healthy = $true
            break
        }
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $healthy) {
    throw "AppLab no respondio. Revisa $stderrLog"
}

& $tailscale serve --bg --yes http://127.0.0.1:5000
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo configurar Tailscale Serve."
}

Write-Host ""
Write-Host "AppLab esta disponible de forma privada en:"
& $tailscale serve status
