@echo off
setlocal

title FamousRelatives Launcher

REM ==========================
REM ROOT
REM ==========================
set "ROOT=%~dp0"
set "ENV_FILE=%ROOT%.env"
set "PROFILE_DIR=%ROOT%chrome_debug_profile"

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
    docker-compose up -d db
    timeout /t 5 /nobreak >nul
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

REM ==========================
REM LISTENER
REM ==========================
cd /d "%ROOT%listener"
start "Listener" cmd /k "node listen.js"

timeout /t 3 /nobreak >nul

REM ==========================
REM BROWSER FLOW
REM ==========================

if "%OPCION%"=="1" (
    start "" "%BROWSER%" ^
    --remote-debugging-port=9222 ^
    --user-data-dir="%PROFILE_DIR%" ^
    --disable-session-restore ^
    --no-first-run ^
    --new-window ^
    --start-maximized ^
    "https://www.familysearch.org/en/global"
) else (
    start "" "%BROWSER%" ^
    --remote-debugging-port=9222 ^
    --user-data-dir="%PROFILE_DIR%" ^
    --new-window ^
    --start-maximized ^
    "https://www.familysearch.org/en/global"
)

timeout /t 5 /nobreak >nul

echo.
echo Esperando token del listener...
echo.

REM ==========================
REM WAIT TOKEN
REM ==========================
:WAIT_TOKEN
timeout /t 2 >nul

if exist "%ENV_FILE%" (
    for /f "tokens=2 delims==" %%T in ('findstr /r "^FAMILYSEARCH_TOKEN=" "%ENV_FILE%"') do (
        if not "%%T"=="" (
            echo Token detectado en .env. Abriendo app raiz y procesando...
            start "" "%BROWSER%" ^
            --user-data-dir="%PROFILE_DIR%" ^
            --start-maximized ^
            "http://localhost:5000/"
            goto END
        )
    )
)

goto WAIT_TOKEN

:END
echo.
echo Sistema listo.
pause