#!/bin/bash
# Construye iClapp.app (sin firmar) con py2app.
# Resultado: dist/iClapp.app  — arrástralo a /Applications.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
fi
echo "📦 Instalando dependencias de build (py2app + runtime)..."
./.venv/bin/pip install --quiet -r requirements.txt py2app

echo "🧹 Limpiando builds anteriores..."
rm -rf build dist

echo "🔨 Construyendo iClapp.app..."
./.venv/bin/python setup.py py2app

echo
echo "✅ Listo: dist/iClapp.app"
echo "   Pruébalo:  open dist/iClapp.app"
echo "   Instálalo: arrástralo a la carpeta Aplicaciones."
echo "   (App sin firmar: la 1ª vez ábrela con clic derecho → Abrir.)"
