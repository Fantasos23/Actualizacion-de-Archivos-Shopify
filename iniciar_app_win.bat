@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
title Centro de Sincronización SERPI - Shopify

:: -------------------------------------------------------------
:: 1. FIJAR DIRECTORIO DE TRABAJO
:: Fundamental cuando se ejecuta con clic derecho "Ejecutar como administrador"
:: ya que Windows por defecto inicia en C:\Windows\System32
:: -------------------------------------------------------------
cd /d "%~dp0"

echo ================================================================
echo    LIBRERIA TROYA - CENTRO DE SINCRONIZACION SERPI Y SHOPIFY
echo ================================================================
echo.

:: -------------------------------------------------------------
:: 2. DETECTAR PYTHON EN EL SISTEMA
:: -------------------------------------------------------------
echo [*] Verificando instalación de Python...

set "PYTHON_EXE="

:: Probar comando directo 'python'
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=python"
    goto :PYTHON_ENCONTRADO
)

:: Probar Python Launcher de Windows 'py'
py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=py -3"
    goto :PYTHON_ENCONTRADO
)

:: Buscar en rutas típicas de instalación de usuario en Windows
for /d %%i in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%i\python.exe" (
        set "PYTHON_EXE=%%i\python.exe"
        goto :PYTHON_ENCONTRADO
    )
)

:: Buscar en rutas típicas de Program Files
for /d %%i in ("%ProgramFiles%\Python3*") do (
    if exist "%%i\python.exe" (
        set "PYTHON_EXE=%%i\python.exe"
        goto :PYTHON_ENCONTRADO
    )
)

:PYTHON_ENCONTRADO
if "%PYTHON_EXE%"=="" (
    echo.
    echo ================================================================
    echo [ERROR] No se encontro ninguna instalacion de Python en este equipo.
    echo ================================================================
    echo.
    echo Por favor descarga e instala Python desde:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Durante la instalacion, asegurate de marcar la casilla:
    echo   "[X] Add python.exe to PATH"
    echo.
    pause
    exit /b 1
)

echo [OK] Python detectado correctamente:
%PYTHON_EXE% --version
echo.

:: -------------------------------------------------------------
:: 3. CREAR / VERIFICAR ENTORNO VIRTUAL (.venv)
:: -------------------------------------------------------------
echo [*] Configurando entorno virtual (.venv)...

if not exist ".venv\Scripts\python.exe" (
    echo [*] Creando entorno virtual aislado (.venv) por primera vez...
    %PYTHON_EXE% -m venv .venv
    if !errorlevel! neq 0 (
        echo [AVISO] No se pudo crear el entorno virtual. Se usara la instalacion global de Python.
        set "ENV_PY=%PYTHON_EXE%"
    ) else (
        echo [OK] Entorno virtual creado exitosamente.
        set "ENV_PY=.venv\Scripts\python.exe"
    )
) else (
    echo [OK] Entorno virtual existente detectado.
    set "ENV_PY=.venv\Scripts\python.exe"
)
echo.

:: -------------------------------------------------------------
:: 4. INSTALACION / ACTUALIZACION DE DEPENDENCIAS
:: -------------------------------------------------------------
echo ================================================================
echo    Instalando y verificando librerias requeridas (requirements.txt)
echo ================================================================
echo.

echo [*] Actualizando pip...
%ENV_PY% -m pip install --upgrade pip --quiet

if exist "requirements.txt" (
    echo [*] Instalando dependencias desde requirements.txt...
    %ENV_PY% -m pip install -r requirements.txt
) else (
    echo [*] Instalando dependencias principales...
    %ENV_PY% -m pip install streamlit pandas requests python-dotenv openpyxl
)

if !errorlevel! neq 0 (
    echo.
    echo [AVISO] Hubo un inconveniente con el entorno virtual.
    echo Intentando instalacion en el usuario de Windows...
    %PYTHON_EXE% -m pip install streamlit pandas requests python-dotenv openpyxl
    set "ENV_PY=%PYTHON_EXE%"
)

echo.
echo [OK] Todas las dependencias estan verificadas e instaladas.
echo.

:: -------------------------------------------------------------
:: 5. VERIFICACION DE ARCHIVOS CRITICOS
:: -------------------------------------------------------------
if not exist "app.py" (
    echo [ERROR] No se encontro 'app.py' en la carpeta: %cd%
    echo Asegurate de que este archivo .bat este en la misma carpeta que app.py.
    pause
    exit /b 1
)

if not exist ".env" (
    echo.
    echo ================================================================
    echo [AVISO] No se encontro el archivo de credenciales '.env'.
    echo Recuerda crear o copiar tu archivo '.env' con las claves de
    echo Shopify y SERPI para que la aplicacion pueda conectarse.
    echo ================================================================
    echo.
)

:: -------------------------------------------------------------
:: 6. INICIAR STREAMLIT
:: -------------------------------------------------------------
echo ================================================================
echo    Iniciando aplicacion en el navegador web...
echo ================================================================
echo.

if exist ".venv\Scripts\streamlit.exe" (
    ".venv\Scripts\streamlit.exe" run app.py
) else (
    %ENV_PY% -m streamlit run app.py
)

if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Streamlit se detuvo inesperadamente.
    pause
)