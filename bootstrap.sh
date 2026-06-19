#!/bin/bash
# 👏 iClap — instalador de un solo comando.
#
# Para tus amigos. Dos formas de usarlo:
#
#   1) One-liner (no hace falta descargar nada):
#      curl -fsSL https://raw.githubusercontent.com/papopelo/iClap/master/bootstrap.sh | bash
#
#   2) Con el archivo descargado:
#      bash bootstrap.sh
#
# Clona iClap en ~/iClap (o actualiza si ya existe) y corre el instalador.
set -e

REPO="https://github.com/papopelo/iClap.git"
DIR="$HOME/iClap"

echo "👏 iClap — instalación automática"
echo

# 1) Requisitos: git y python3 (en macOS, invocarlos dispara la instalación de
#    las Command Line Tools si faltan).
need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "❌ Falta '$1'. En macOS instálalo con:  xcode-select --install"
    echo "   (acepta el diálogo, espera a que termine y vuelve a correr esto)."
    exit 1
  fi
}
need git
need python3

# 2) Clonar o actualizar
if [ -d "$DIR/.git" ]; then
  echo "📂 Ya existe ~/iClap; actualizando..."
  git -C "$DIR" pull --ff-only
else
  if [ -e "$DIR" ]; then
    echo "❌ Existe ~/iClap pero no es un repo de git. Muévelo o bórralo y reintenta."
    exit 1
  fi
  echo "📥 Clonando iClap en ~/iClap..."
  git clone --quiet "$REPO" "$DIR"
fi

# 3) Instalar (crea venv, config y carga el servicio)
cd "$DIR"
chmod +x install.sh run.sh uninstall.sh 2>/dev/null || true
./install.sh
