"""App de barra de menú (rumps).

Vive en la barra de menú (👏), escucha en segundo plano y reproduce al detectar
doble aplauso. La ventana de Preferencias se abre como proceso aparte para no
chocar con el loop de Cocoa y para liberar el micrófono al calibrar.
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import rumps

from . import config
from .engine import ClapEngine
from .players import play

_LOG = Path.home() / "Library" / "Logs" / "iClap.log"


def _log(msg):
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_LOG, "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:  # noqa: BLE001
        pass


def _spawn_prefs():
    """Lanza la ventana de Preferencias como proceso independiente."""
    env = {**os.environ, "ICLAP_MODE": "prefs"}
    if getattr(sys, "frozen", False):
        # Dentro del .app: el mismo ejecutable, en modo prefs (ver iclap_app.py).
        cmd = [sys.executable]
    else:
        cmd = [sys.executable, "-m", "iclap.prefs"]
    _log(f"spawn prefs: frozen={getattr(sys, 'frozen', False)} cmd={cmd}")
    return subprocess.Popen(cmd, env=env)


class IClapApp(rumps.App):
    def __init__(self):
        super().__init__("👏", quit_button=None)
        self.engine = None
        self.status_item = rumps.MenuItem("Iniciando…")
        self.toggle_item = rumps.MenuItem("Pausar", callback=self.toggle)
        self.menu = [
            self.status_item,
            None,
            rumps.MenuItem("Preferencias…", callback=self.open_prefs),
            self.toggle_item,
            None,
            rumps.MenuItem("Salir iClap", callback=self.quit_app),
        ]
        self.start_engine()

    # --- Motor ---
    def start_engine(self):
        cfg = config.load()
        self.engine = ClapEngine(
            on_double_clap=self.on_clap,
            threshold=cfg["threshold"],
            max_clap_ms=cfg["max_clap_ms"],
            input_device=cfg.get("input_device"),
        )
        try:
            self.engine.start()
            mic = cfg.get("input_device") or "micrófono por defecto"
            self.status_item.title = f"🎧 Escuchando · {mic}"
            self.toggle_item.title = "Pausar"
        except Exception as e:  # noqa: BLE001
            self.status_item.title = "⚠️ Error de micrófono (revisa permisos)"

    def stop_engine(self):
        if self.engine:
            self.engine.stop()

    def on_clap(self):
        cfg = config.load()
        ok, msg = play(cfg["url"], cfg.get("shuffle", True))
        try:
            rumps.notification("iClap", "👏👏", msg)
        except Exception:  # noqa: BLE001
            pass

    # --- Menú ---
    def toggle(self, _):
        if self.engine and self.engine.running:
            self.stop_engine()
            self.status_item.title = "⏸️ En pausa"
            self.toggle_item.title = "Reanudar"
        else:
            self.start_engine()

    def open_prefs(self, _):
        # Liberar el micrófono mientras Preferencias está abierta (para calibrar).
        was_running = self.engine and self.engine.running
        self.stop_engine()
        self.status_item.title = "⚙️ Preferencias abiertas…"

        def wait_and_reload():
            try:
                proc = _spawn_prefs()
                proc.wait()
                _log(f"prefs cerrado (rc={proc.returncode})")
            except Exception as e:  # noqa: BLE001
                _log(f"error al abrir prefs: {e}")
            # Al cerrar la ventana, recargar config y volver a escuchar.
            if was_running:
                self.start_engine()
            else:
                self.status_item.title = "⏸️ En pausa"

        threading.Thread(target=wait_and_reload, daemon=True).start()

    def quit_app(self, _):
        self.stop_engine()
        rumps.quit_application()


def main():
    IClapApp().run()


if __name__ == "__main__":
    main()
