#!/bin/bash
# iClapp — crea el venv la primera vez e inicia el detector de aplausos.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "📦 Creando entorno virtual e instalando dependencias..."
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt
fi

exec ./.venv/bin/python -m iclapp "$@"
