#!/bin/bash
# Desinstala iClap: descarga el servicio y borra el LaunchAgent.
# No borra tu carpeta del proyecto ni tu config.json.
set -e

LABEL="com.iclap.detector"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$PLIST"
echo "🧹 iClap desinstalado (servicio descargado y LaunchAgent borrado)."
echo "   Tu carpeta y config.json siguen intactos."
