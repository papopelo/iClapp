"""Modo headless de iClap: escucha y reproduce, sin interfaz.

Lo usa el LaunchAgent (segundo plano). Para la app con interfaz, ver iclap.app.

    python -m iclap                 # escuchar
    python -m iclap --calibrate     # recalibrar por terminal
    python -m iclap --list-devices  # ver micrófonos disponibles
"""

import argparse
import sys
import time

from . import config
from .calibrate import run_cli as calibrate_cli
from .engine import ClapEngine, list_input_devices
from .players import play


def main():
    parser = argparse.ArgumentParser(description="iClap — música al aplaudir dos veces.")
    parser.add_argument("--calibrate", action="store_true",
                        help="Mide tus aplausos y ajusta la sensibilidad.")
    parser.add_argument("--list-devices", action="store_true",
                        help="Lista los micrófonos de entrada disponibles.")
    parser.add_argument("--url", help="Sobrescribe la URL a reproducir.")
    parser.add_argument("--no-shuffle", action="store_true", help="Sin shuffle.")
    args = parser.parse_args()

    if args.list_devices:
        for name, idx in list_input_devices():
            print(f"  [{idx}] {name}")
        return

    if args.calibrate:
        calibrate_cli()
        return

    cfg = config.load()
    url = args.url or cfg["url"]
    shuffle = cfg["shuffle"] and not args.no_shuffle

    def on_clap():
        print("👏👏 doble aplauso")
        ok, msg = play(url, shuffle)
        print(("✅ " if ok else "⚠️  ") + msg, file=sys.stdout if ok else sys.stderr)

    engine = ClapEngine(
        on_double_clap=on_clap,
        threshold=cfg["threshold"],
        max_clap_ms=cfg["max_clap_ms"],
        input_device=cfg.get("input_device"),
    )
    engine.start()
    mic = cfg.get("input_device") or "por defecto"
    print(f"🎧 Escuchando (micro: {mic}, umbral={cfg['threshold']}, "
          f"dur.máx≈{cfg['max_clap_ms']}ms). Aplaude DOS veces. Ctrl+C para salir.")
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n👋 Hasta luego.")
    finally:
        engine.stop()


if __name__ == "__main__":
    main()
