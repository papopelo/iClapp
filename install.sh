#!/bin/bash
# Instalador de clap-spotify para macOS.
# Crea el entorno, deja tu config lista y arranca el detector al iniciar sesión.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.clapspotify.detector"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="$DIR/.venv/bin/python"

cd "$DIR"

echo "👏 Instalando clap-spotify en: $DIR"

# 1) Entorno virtual + dependencias
if [ ! -d ".venv" ]; then
  echo "📦 Creando entorno virtual e instalando dependencias..."
  python3 -m venv .venv
  "$DIR/.venv/bin/pip" install --quiet --upgrade pip
  "$DIR/.venv/bin/pip" install --quiet -r requirements.txt
fi

# 2) Config personal (no se sobrescribe si ya existe)
if [ ! -f "config.json" ]; then
  cp config.example.json config.json
  echo "📝 Creado config.json. Edítalo y pon tu playlist (o usa --playlist)."
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
        <string>$DIR/clap_play.py</string>
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
    <string>$DIR/clap.log</string>
    <key>StandardErrorPath</key>
    <string>$DIR/clap.err</string>
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

   1) Edita tu playlist:   nano "$DIR/config.json"
   2) Calibra tus aplausos: "$DIR/run.sh" --calibrate
      (esto también dispara el diálogo de permiso de micrófono;
       acéptalo y luego reinicia el servicio)
   3) Reinicia el servicio:
      launchctl kickstart -k "gui/$(id -u)/$LABEL"

Luego: aplaude DOS veces 👏👏 y suena tu playlist.
Logs:  tail -f "$DIR/clap.log"
────────────────────────────────────────────────────────
MSG
