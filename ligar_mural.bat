@echo off
setlocal enabledelayedexpansion

rem === CONFIGURAÇÃO ===
set "APPDIR=C:\mural-escola\stable\v1.0.6-rc.4"
set "PYTHON=py"              rem usa o launcher do Windows (py) para achar o Python correto
set "ENTRY=app.py"
set "WTITLE=Mural-App"
set "PY_CMD=%PYTHON% %ENTRY%"

rem === FUNÇÕES ===
:kill_running
    rem Mata qualquer processo python rodando com o comando do app
    for /f "skip=1 tokens=2 delims=," %%P in ('wmic process where "CommandLine like '%%%ENTRY%%%' and name='python.exe'" get ProcessId /format:csv 2^>nul') do (
        if not "%%P"=="" (
            echo Encerrando PID %%P ...
            taskkill /PID %%P /F >nul 2>&1
        )
    )
    rem Também tenta pelo título de janela, se existir
    taskkill /FI "WINDOWTITLE eq %WTITLE%" /F >nul 2>&1
    goto :eof

:start_app
    pushd "%APPDIR%"
    rem Abre em nova janela com título exclusivo
    start "%WTITLE%" cmd /c "%PY_CMD%"
    popd
    goto :eof

rem === MENU ===
:menu
cls
echo ===========================================
echo   Mural Digital - Controle
echo   Pasta: %APPDIR%
echo   Script: %ENTRY%
echo ===========================================
echo   1) Iniciar
echo   2) Reiniciar
echo   3) Parar
echo   0) Sair
echo ===========================================
set /p CH=Escolha: 

if "%CH%"=="1" call :start_app
if "%CH%"=="2" call :kill_running & call :start_app
if "%CH%"=="3" call :kill_running
if "%CH%"=="0" exit /b

goto menu
``