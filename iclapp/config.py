"""Carga/guarda la configuración de iClapp.

La config vive en ~/Library/Application Support/iClapp/config.json para que
funcione tanto desde el CLI como desde el .app (un bundle no puede escribir
dentro de sí mismo). Si no existe, se migra desde la ubicación antigua
(~/iClapp/config.json) para no perder la playlist ni la calibración.
"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / "Library" / "Application Support" / "iClapp"
CONFIG_PATH = CONFIG_DIR / "config.json"

# Ubicaciones antiguas, solo para migrar la config existente (orden de prioridad).
LEGACY_PATHS = [
    Path.home() / "Library" / "Application Support" / "iClap" / "config.json",
    Path.home() / "iClapp" / "config.json",
    Path.home() / "iClap" / "config.json",
    Path.home() / "clap-spotify" / "config.json",
]

DEFAULTS = {
    "url": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",  # muestra: Today's Top Hits
    "threshold": 0.45,
    "max_clap_ms": 160,
    "shuffle": True,
    "input_device": None,   # nombre del micrófono, o None = dispositivo por defecto
}


def _coerce(raw):
    """Normaliza un dict crudo (acepta el viejo 'playlist_uri' como 'url')."""
    cfg = dict(DEFAULTS)
    if "playlist_uri" in raw and "url" not in raw:
        raw = {**raw, "url": raw["playlist_uri"]}
    cfg.update({k: raw[k] for k in DEFAULTS if k in raw})
    return cfg


def load():
    """Devuelve la config (migrando desde la ubicación antigua si hace falta)."""
    if CONFIG_PATH.exists():
        try:
            return _coerce(json.loads(CONFIG_PATH.read_text()))
        except (json.JSONDecodeError, OSError):
            return dict(DEFAULTS)

    # No hay config nueva: intentar migrar desde la antigua.
    for legacy in LEGACY_PATHS:
        if legacy.exists():
            try:
                cfg = _coerce(json.loads(legacy.read_text()))
                save(cfg)
                return cfg
            except (json.JSONDecodeError, OSError):
                pass
    return dict(DEFAULTS)


def save(updates):
    """Mezcla `updates` sobre la config actual y la escribe; devuelve la final."""
    current = {}
    if CONFIG_PATH.exists():
        try:
            current = _coerce(json.loads(CONFIG_PATH.read_text()))
        except (json.JSONDecodeError, OSError):
            current = dict(DEFAULTS)
    else:
        current = dict(DEFAULTS)
    current.update({k: v for k, v in updates.items() if k in DEFAULTS})
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")
    return current
