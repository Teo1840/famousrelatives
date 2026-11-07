# Stops every process belonging to this project (FamousRelatives), so
# start-system.bat can be re-run at any time without stacking up duplicate
# instances. Matches by command-line content, not just by port, because the
# Werkzeug reloader's parent process never binds a port but still needs to die.
#
# Safety boundary: only touches brave.exe / node.exe / python.exe / pythonw.exe /
# cmd.exe processes whose command line matches this project's known scripts
# (app.py, fs_proxy.py, listen.js) or the token-capture Brave flags/profile dir.
# Never does a blanket taskkill by image name alone.
[CmdletBinding()]
param(
    [ValidateSet("All", "CaptureOnly")]
    [string]$Scope = "All",
    [switch]$Quiet
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProfileDir = Join-Path $Root "chrome_debug_profile"
$ProfileDirEscaped = [regex]::Escape($ProfileDir)

function Write-Info($msg) {
    if (-not $Quiet) { Write-Host $msg }
}

function Stop-Matching {
    param([string[]]$ProcessNames, [string]$Pattern, [string]$Label)
    $procs = Get-CimInstance Win32_Process | Where-Object {
        $ProcessNames -contains $_.Name -and $_.CommandLine -and ($_.CommandLine -match $Pattern)
    }
    foreach ($p in $procs) {
        Write-Info "  Deteniendo $Label (PID $($p.ProcessId)): $($p.CommandLine)"
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
        } catch {
            Write-Warning "  No se pudo detener PID $($p.ProcessId): $_"
        }
    }
}

Write-Info "=== Deteniendo procesos de FamousRelatives (Scope=$Scope) ==="

# 1. node listen.js - siempre.
Stop-Matching -ProcessNames @('node.exe') -Pattern '(?i)listen\.js' -Label "listener (node listen.js)"

if ($Scope -eq "All") {
    # 2. Brave de la app (puerto 9222 / chrome_debug_profile). Es la misma
    #    ventana donde corre la app y el capturador, asi que solo se cierra
    #    al reiniciar o detener todo el sistema, nunca en una captura.
    $bravePattern = '(?i)(--remote-debugging-port=9222|' + $ProfileDirEscaped + ')'
    Stop-Matching -ProcessNames @('brave.exe') -Pattern $bravePattern -Label "Brave (app y captura de token)"

    # 3. app.py - matchea tanto el proceso padre (reloader) como el worker de
    #    Werkzeug, y tanto python.exe del venv como uno global del PATH,
    #    porque el match es por contenido de linea de comando, no por ruta.
    $appPattern = '(?i)(^|[\\/\s"])app\.py([\s"]|$)'
    Stop-Matching -ProcessNames @('python.exe', 'pythonw.exe') -Pattern $appPattern -Label "app.py"
    Stop-Matching -ProcessNames @('cmd.exe') -Pattern $appPattern -Label "ventana Flask App"

    # 4. fs_proxy.py - misma idea.
    $proxyPattern = '(?i)fs_proxy\.py'
    Stop-Matching -ProcessNames @('python.exe', 'pythonw.exe') -Pattern $proxyPattern -Label "fs_proxy.py"
    Stop-Matching -ProcessNames @('cmd.exe') -Pattern $proxyPattern -Label "ventana Proxy"
}

Start-Sleep -Milliseconds 500

$ports = if ($Scope -eq "All") { @(5000, 5001, 9222) } else { @() }
foreach ($port in $ports) {
    $listening = netstat -ano | Select-String ":$port\s.*LISTENING"
    if ($listening) {
        Write-Warning "Puerto $port sigue en uso: $listening"
    } else {
        Write-Info "  Puerto $port libre."
    }
}

Write-Info "=== Limpieza completa ==="
