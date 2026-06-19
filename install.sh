#!/bin/bash
# Instalador de iClapp para macOS.
# Crea el entorno, deja tu config lista y arranca el detector al iniciar sesión.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.iclapp.detector"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="$DIR/.venv/bin/python"

cd "$DIR"

echo "👏 Instalando iClapp en: $DIR"

# 0) Aviso si Spotify no está instalado (no bloqueante: se puede instalar luego)
if ! osascript -e 'id of application "Spotify"' >/dev/null 2>&1; then
  echo
  echo "⚠️  No encuentro la app de Spotify de escritorio."
  echo "   iClapp la necesita para reproducir. Instálala desde https://www.spotify.com/download"
  echo "   (puedes seguir; solo recuerda instalar Spotify antes de aplaudir)."
  echo
fi

# 1) Entorno virtual + dependencias
if [ ! -d ".venv" ]; then
  echo "📦 Creando entorno virtual e instalando dependencias..."
  python3 -m venv .venv
  "$DIR/.venv/bin/pip" install --quiet --upgrade pip
  "$DIR/.venv/bin/pip" install --quiet -r requirements.txt
fi

# 2) Config personal en Application Support (la usa tanto el CLI como el .app)
CONFIG_DIR="$HOME/Library/Application Support/iClapp"
CONFIG="$CONFIG_DIR/config.json"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG" ]; then
  cp config.example.json "$CONFIG"
  echo "📝 Creado $CONFIG — edítalo y pon tu URL."
fi

# 3) Generar el LaunchAgent con las rutas de ESTE usuario
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PY</string>
        <string>-m</string>
        <string>iclapp</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>WorkingDirectory</key>
    <string>$DIR</string>
    <key>StandardOutPath</key>
    <string>$DIR/iclapp.log</string>
    <key>StandardErrorPath</key>
    <string>$DIR/iclapp.err</string>
</dict>
</plist>
PLIST_EOF
echo "🧩 LaunchAgent escrito en $PLIST"

# 4) (Re)cargar el servicio
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "🚀 Servicio cargado."

# 5) Permiso de micrófono: un proceso de launchd no puede pedirlo solo.
#    Hay que correr el script UNA vez desde Terminal para que macOS muestre
#    el diálogo y conceda el permiso al binario de Python del venv.
cat <<MSG

────────────────────────────────────────────────────────
✅ Casi listo. Falta UN paso (permiso de micrófono):

   1) Edita tu URL:        nano "$CONFIG"
   2) Calibra tus aplausos: "$DIR/run.sh" --calibrate
      (esto también dispara el diálogo de permiso de micrófono;
       acéptalo y luego reinicia el servicio)
   3) Reinicia el servicio:
      launchctl kickstart -k "gui/$(id -u)/$LABEL"

Luego: aplaude DOS veces 👏👏 y suena tu música.
Logs:  tail -f "$DIR/iclapp.log"
────────────────────────────────────────────────────────
MSG
