@echo off
setlocal

title FamousRelatives Launcher

REM ==========================
REM ROOT
REM ==========================
set "ROOT=%~dp0"
set "ENV_FILE=%ROOT%.env"
set "PROFILE_DIR=%ROOT%chrome_debug_profile"

REM ==========================
REM CLEANUP: kill any leftover instance from a previous run before
REM launching new ones, so re-running this script always converges to
REM exactly one stack instead of piling on more.
REM ==========================
echo Deteniendo instancias previas (si existen)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%stop-system.ps1" -Scope All -Quiet
echo.

REM Remove any existing token entry and ensure the token is empty before each run.
if exist "%ENV_FILE%" (
    >"%ROOT%.env.tmp" (
        for /f "usebackq delims=" %%L in ("%ENV_FILE%") do (
            echo %%L| findstr /b /c:"FAMILYSEARCH_TOKEN=" >nul
            if errorlevel 1 echo %%L
        )
    )
) else (
    type nul >"%ROOT%.env.tmp"
)
echo FAMILYSEARCH_TOKEN=>>"%ROOT%.env.tmp"
move /y "%ROOT%.env.tmp" "%ENV_FILE%" >nul

set "PYTHON=python"
set "NODE=node"
set "BROWSER=C:\Users\abc\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"

REM Without this, Python's stdout defaults to the console's codepage (not UTF-8),
REM and the emoji in db.py's startup prints crashes init_db() before MySQL even connects.
set "PYTHONIOENCODING=utf-8"

echo =====================================
echo FamousRelatives Launcher
echo =====================================
echo.
echo ROOT = %ROOT%
echo.

echo Iniciando sistema en limpio...
echo.

echo Limpiando perfil Brave...
if exist "%PROFILE_DIR%" rd /s /q "%PROFILE_DIR%"

REM ==========================
REM DOCKER - DB ONLY
REM ==========================
cd /d "%ROOT%"

echo Verificando Docker...
set "DOCKER_AVAILABLE=0"
2>nul docker info >nul 2>&1 && set "DOCKER_AVAILABLE=1"

if "%DOCKER_AVAILABLE%"=="1" (
    echo Docker disponible. Iniciando MySQL container...
    echo Esperando a que MySQL este listo para aceptar conexiones...
    docker-compose up -d --wait db
    if errorlevel 1 (
        echo.
        echo ADVERTENCIA: MySQL no llego a estar healthy a tiempo.
        echo La app va a reintentar la conexion igual, pero puede tardar.
        echo.
    )
) else (
    echo.
    echo ADVERTENCIA: Docker no esta disponible.
    echo Asegúrate de que MySQL este ejecutándose localmente en localhost:3306
    echo con usuario: root, contraseña: secret
    echo.
)

REM ==========================
REM PROXY
REM ==========================
cd /d "%ROOT%"
start "Proxy" cmd /k "call venv\Scripts\activate.bat && python fs_proxy.py"

REM ==========================
REM FLASK APP
REM ==========================
cd /d "%ROOT%"
start "Flask App" cmd /k "call venv\Scripts\activate.bat && python app.py"

timeout /t 3 /nobreak >nul

REM ==========================
REM BROWSER: abrir directo la app
REM ==========================
REM Se abre con el puerto de depuracion 9222 y un perfil propio para que el
REM boton "Ejecutar capturador de token" abra FamilySearch en una pestana
REM nueva de esta misma ventana (listener\listen.js) en vez de otro Brave.
start "" "%BROWSER%" ^
--remote-debugging-port=9222 ^
--user-data-dir="%PROFILE_DIR%" ^
--no-first-run ^
--start-maximized ^
"http://localhost:5000/"

echo.
echo Sistema listo.
pause