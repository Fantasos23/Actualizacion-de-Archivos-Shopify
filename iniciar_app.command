#!/bin/bash

# 1. Posicionarse en la carpeta donde está guardado este archivo
cd "$(dirname "$0")"

echo "=================================================="
echo "🚀 Sincronizando repositorio con GitHub..."
echo "=================================================="

# 2. Guardar cambios en Git y subirlos
git add .
git commit -m "Auto-update desde ejecutable local: $(date +'%Y-%m-%d %H:%M:%S')"
git push origin main || git push origin master

echo ""
echo "=================================================="
echo "📦 Iniciando Gestor de Inventario en Streamlit..."
echo "=================================================="

# 3. Activar el entorno o ejecutar Streamlit directamente
if command -v streamlit &> /dev/null
then
    streamlit run app.py
else
    python3 -m streamlit run app.py
fi