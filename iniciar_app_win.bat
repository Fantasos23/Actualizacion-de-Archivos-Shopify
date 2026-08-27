@echo off
chcp 65001 > nul
title Iniciador de Aplicación Streamlit

echo =======================================================
echo    1. Verificando instalación de Python en Windows
echo =======================================================
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no está instalado o no está configurado en el PATH.
    echo Por favor instala Python o agrégalo a las variables de entorno.
    pause
    exit /b
)

echo =======================================================
echo    2. Verificando e instalando librerías requeridas
echo =======================================================

:: Verificar e instalar 'requests'
python -c "import requests" > nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Instalando requests...
    python -m pip install requests
) else (
    echo [OK] requests ya está instalado.
)

:: Verificar e instalar 'streamlit'
python -c "import streamlit" > nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Instalando streamlit...
    python -m pip install streamlit
) else (
    echo [OK] streamlit ya está instalado.
)

:: Verificar e instalar 'pandas'
python -c "import pandas" > nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Instalando pandas...
    python -m pip install pandas
) else (
    echo [OK] pandas ya está instalado.
)

:: Verificar e instalar 'python-dotenv' (para load_dotenv)
python -c "from dotenv import load_dotenv" > nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Instalando python-dotenv...
    python -m pip install python-dotenv
) else (
    echo [OK] python-dotenv ya está instalado.
)

:: Verificar e instalar 'openpyxl' (para soporte Excel en pandas)
python -c "import openpyxl" > nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Instalando openpyxl...
    python -m pip install openpyxl
) else (
    echo [OK] openpyxl ya está instalado.
)

echo =======================================================
echo    3. Verificando archivos del proyecto
echo =======================================================
if not exist "subir_imagenes.py" (
    echo [ALERTA] No se encontró 'subir_imagenes.py' en este directorio.
)
if not exist "app.py" (
    echo [ERROR] No se encontró el archivo 'app.py'.
    pause
    exit /b
)

echo =======================================================
echo    4. Iniciando Streamlit (app.py)
echo =======================================================
python -m streamlit run app.py

pause