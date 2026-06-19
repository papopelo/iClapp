"""Calibración: mide N aplausos y deduce threshold + max_clap_ms.

Resuelve el problema central del proyecto (la sensibilidad depende del micro y
de las manos de cada uno). Usable desde la GUI (con callback de progreso) o
desde el CLI (`python -m iclapp.calibrate`).
"""

import sys
import time

import numpy as np
import sounddevice as sd

from . import config
from .engine import BLOCK_MS, BLOCKSIZE, SAMPLERATE, _device_index

CAPTURE_FLOOR = 0.05   # entra a "racha" cualquier sonido por encima de esto
CAPTURE_MIN = 0.12     # pico mínimo para contar como aplauso (no roce/ruido)
TIMEOUT_S = 30.0       # no esperar para siempre si el micro no oye
MIN_CLAPS = 3          # con 3 ya se puede calibrar; ideal n


def measure(n=5, input_device=None, on_clap=None, should_stop=None):
    """Captura hasta `n` aplausos. Devuelve lista de (pico, duración_ms).

    `on_clap(i, n, pico, dur)` se llama por cada aplauso detectado (para la UI).
    `should_stop()` permite cancelar desde fuera (la GUI).
    """
    claps = []
    run = {"len": 0, "peak": 0.0}

    def cb(indata, frames, time_info, status):
        peak = float(np.abs(indata).max())
        if peak >= CAPTURE_FLOOR:
            run["len"] += 1
            run["peak"] = max(run["peak"], peak)
        elif run["len"] > 0:
            dur = run["len"] * BLOCK_MS
            rpeak = run["peak"]
            run["len"] = 0
            run["peak"] = 0.0
            if rpeak >= CAPTURE_MIN and dur <= 400:
                claps.append((rpeak, dur))
                if on_clap:
                    on_clap(len(claps), n, rpeak, dur)

    with sd.InputStream(channels=1, samplerate=SAMPLERATE, blocksize=BLOCKSIZE,
                        device=_device_index(input_device), callback=cb):
        start = time.monotonic()
        while len(claps) < n and (time.monotonic() - start) < TIMEOUT_S:
            if should_stop and should_stop():
                break
            time.sleep(0.05)
    return claps


def params_from(claps):
    """Deduce (threshold, max_clap_ms) de los aplausos medidos, o None si pocos."""
    if len(claps) < MIN_CLAPS:
        return None
    peaks = [p for p, _ in claps]
    durs = [d for _, d in claps]
    threshold = round(max(0.1, min(peaks) * 0.7), 2)
    max_clap_ms = int(round(max(durs) * 1.3 / 10.0) * 10)
    return threshold, max_clap_ms


def run_cli(n=5):
    """Calibración interactiva por terminal; guarda en config."""
    print(f"🎚️  Calibración: aplaude {n} veces, una a una, con ~1 s entre cada una.")
    print("   (Ctrl+C para cancelar)\n")
    cfg = config.load()

    def on_clap(i, total, peak, dur):
        print(f"   👏 {i}/{total}  pico:{peak:5.3f}  dur:{dur:4.0f}ms")

    try:
        claps = measure(n=n, input_device=cfg.get("input_device"), on_clap=on_clap)
    except KeyboardInterrupt:
        print("\n✋ Cancelada.")
        return

    params = params_from(claps)
    if params is None:
        print(f"\n⚠️  Solo detecté {len(claps)} aplauso(s). Revisa el permiso de "
              "micrófono y aplaude más fuerte/cerca; reintenta.")
        return
    threshold, max_clap_ms = params
    config.save({"threshold": threshold, "max_clap_ms": max_clap_ms})
    print(f"\n✅ Calibrado: threshold={threshold}, max_clap_ms={max_clap_ms} (guardado).")


if __name__ == "__main__":
    run_cli()
