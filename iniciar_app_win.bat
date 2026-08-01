@echo off
title Gestor Local Shopify - Actualizador de Codigo

:: 1. Ir a la carpeta actual del proyecto
cd /d "%~dp0"

echo ==================================================
echo 🔍 Verificando y descargando cambios de GitHub...
echo ==================================================

:: 2. Limpiar posibles cambios locales temporales no guardados (opcional pero recomendado para evitar conflictos)
git stash

:: 3. Traer y aplicar las últimas actualizaciones del repositorio
git pull origin main || git pull origin master

echo.
echo ==================================================
echo 📦 Iniciando Gestor de Inventario en Streamlit...
echo ==================================================

:: 4. Ejecutar Streamlit
streamlit run app.py

pause