#!/usr/bin/env python3
"""
Detecta dos aplausos seguidos y reproduce
una playlist en Spotify con shuffle activado.

Uso:
    python iclap.py            # modo normal
    python iclap.py --debug    # muestra el nivel de audio para calibrar
    python iclap.py --threshold 0.4
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

# --- Configuración de la playlist --------------------------------------------
# Valor por defecto si no hay config.json. Cada usuario pone la suya en config.json
# (ver config.example.json) o con --playlist. Esta es solo de muestra.
PLAYLIST_URI = "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"  # "Today's Top Hits" (muestra)

# --- Parámetros de detección -------------------------------------------------
SAMPLERATE = 44100        # Hz
BLOCKSIZE = 1024          # muestras por bloque (~23 ms)
DEFAULT_THRESHOLD = 0.45  # pico de amplitud (0..1) para contar como aplauso
DEFAULT_HF_RATIO = 0.0    # filtro de agudos (0 = desactivado; ver --hf-ratio)
HF_CUTOFF = 2000          # Hz: frontera grave/agudo
MAX_CLAP_MS = 160         # ms: duración máxima de un aplauso (más largo = tos/ruido)
                          # Calibrado 2026-06-18: aplausos ≤139ms (6b), voz/tos ≥186ms (8b);
                          # corte en 7 bloques (~162ms) separa limpio ambos.
SUSTAIN_FACTOR = 0.5      # fracción del umbral para medir la "cola" del sonido
BLOCK_MS = 1000.0 * BLOCKSIZE / SAMPLERATE          # ~23 ms por bloque
DEBOUNCE = 0.15           # s: tiempo mínimo entre dos aplausos (anti-rebote)
DOUBLE_WINDOW = 0.80      # s: ventana máxima entre aplauso 1 y aplauso 2
COOLDOWN = 5.0            # s: pausa tras disparar (evita que la música re-dispare)

# Precálculo para el análisis de frecuencia (ventana Hann + máscara de agudos)
_WINDOW = np.hanning(BLOCKSIZE)
_FREQS = np.fft.rfftfreq(BLOCKSIZE, 1.0 / SAMPLERATE)
_HF_MASK = _FREQS >= HF_CUTOFF


def hf_ratio(block):
    """Fracción de energía espectral por encima de HF_CUTOFF (0..1).

    Aplauso (clic de banda ancha) -> alto. Tos/voz (energía grave) -> bajo.
    """
    x = block[:, 0] if block.ndim > 1 else block
    if len(x) != BLOCKSIZE:
        return 0.0
    mag = np.abs(np.fft.rfft(x * _WINDOW))
    total = mag.sum()
    if total < 1e-9:
        return 0.0
    return float(mag[_HF_MASK].sum() / total)


def wea_bakn_spotify(playlist_uri, shuffle=True):
    """Lanza/usa Spotify y reproduce la playlist (en shuffle) vía AppleScript.

    Si Spotify estaba cerrado, al abrirse a veces queda en pausa; por eso
    cargamos la playlist, esperamos un poco y forzamos 'play'. Como 'play track'
    sobre una playlist empieza siempre por la primera pista, al activar el shuffle
    saltamos de pista para arrancar en una canción al azar.
    """
    shuffle_setup = 'set shuffling to true' if shuffle else 'set shuffling to false'
    shuffle_jump = 'next track\n        delay 0.2' if shuffle else ''
    script = f'''
    if application "Spotify" is not running then
        tell application "Spotify" to activate
        delay 1.5
    end if
    tell application "Spotify"
        {shuffle_setup}
        play track "{playlist_uri}"
        delay 0.4
        {shuffle_jump}
        if player state is not playing then play
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], check=True,
                       capture_output=True, text=True)
        print("🎸 ¡Playlist en shuffle!" if shuffle else "🎸 ¡Playlist!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Error al reproducir: {e.stderr.strip()}", file=sys.stderr)


def normalize_playlist(value):
    """Acepta una URI (spotify:playlist:ID) o un enlace web y devuelve la URI.

    Ej.: 'https://open.spotify.com/playlist/ABC?si=xyz' -> 'spotify:playlist:ABC'.
    Así la gente puede pegar lo que copie de Spotify sin pensar en el formato.
    """
    value = value.strip()
    if value.startswith("spotify:"):
        return value
    if "open.spotify.com" in value:
        path = value.split("open.spotify.com/", 1)[1].split("?", 1)[0]
        kind, _, pid = path.strip("/").partition("/")
        if kind and pid:
            return f"spotify:{kind}:{pid}"
    return value  # se deja tal cual; Spotify reportará si es inválida


def load_config():
    """Lee config.json (si existe) y lo mezcla sobre los valores por defecto.

    Cada persona tiene su propio config.json (gitignored); así nadie edita
    el código para poner su playlist o su sensibilidad.
    """
    cfg = {
        "playlist_uri": PLAYLIST_URI,
        "threshold": DEFAULT_THRESHOLD,
        "max_clap_ms": MAX_CLAP_MS,
        "shuffle": True,
    }
    try:
        with open(CONFIG_PATH) as f:
            user = json.load(f)
        cfg.update({k: user[k] for k in cfg if k in user})
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️  config.json inválido ({e}); uso valores por defecto.",
              file=sys.stderr)
    return cfg


def save_config(updates):
    """Mezcla `updates` sobre el config.json actual y lo escribe (preserva el resto)."""
    current = {}
    try:
        with open(CONFIG_PATH) as f:
            current = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    current.update(updates)
    with open(CONFIG_PATH, "w") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return current


def calibrate(n=5):
    """Captura N aplausos reales y deduce umbral + duración para este micro/persona.

    Resuelve el problema central del proyecto: la sensibilidad depende del micro
    y de las manos de cada uno. Mide pico y duración de cada aplauso y deja un
    margen para que detecte de forma fiable sin disparar con ruido.
    """
    print(f"🎚️  Calibración: aplaude {n} veces, una a una, con ~1 s entre cada una.")
    print("   (empieza cuando quieras; Ctrl+C para cancelar)\n")

    # Piso bajo (no DEFAULT_THRESHOLD*SUSTAIN) para no perder aplausos de micros
    # flojos; el filtro real de "esto fue un aplauso" es CAPTURE_MIN abajo.
    CAPTURE_FLOOR = 0.05     # entra a "racha" cualquier sonido por encima de esto
    CAPTURE_MIN = 0.12       # pico mínimo para contar como aplauso (no roce/ruido)
    TIMEOUT_S = 30.0         # no esperar para siempre si el micro no oye
    MIN_CLAPS = 3            # con 3 ya se puede calibrar; ideal n
    claps = []                                   # (pico, duración_ms) por aplauso
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
                print(f"   👏 {len(claps)}/{n}  pico:{rpeak:5.3f}  dur:{dur:4.0f}ms")

    try:
        with sd.InputStream(channels=1, samplerate=SAMPLERATE,
                            blocksize=BLOCKSIZE, callback=cb):
            start = time.monotonic()
            while len(claps) < n and (time.monotonic() - start) < TIMEOUT_S:
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n✋ Calibración cancelada.")
        return

    if len(claps) < MIN_CLAPS:
        print(f"\n⚠️  Solo detecté {len(claps)} aplauso(s) en {TIMEOUT_S:.0f}s.")
        print("   Revisa el permiso de micrófono y aplaude más fuerte/cerca; "
              "luego prueba de nuevo con --calibrate.")
        return

    peaks = [p for p, _ in claps]
    durs = [d for _, d in claps]
    # Umbral: justo por debajo del aplauso más flojo (70%). Duración: por encima
    # del aplauso más largo (1.3x), redondeada a 10 ms.
    threshold = round(max(0.1, min(peaks) * 0.7), 2)
    max_clap_ms = int(round(max(durs) * 1.3 / 10.0) * 10)
    print(f"\n✅ Calibrado: threshold={threshold}, max_clap_ms={max_clap_ms}")
    save_config({"threshold": threshold, "max_clap_ms": max_clap_ms})
    print(f"   Guardado en {CONFIG_PATH.name}. Reinicia el servicio para aplicarlo.")


def main():
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Reproduce una playlist al aplaudir dos veces.")
    parser.add_argument("--threshold", type=float, default=cfg["threshold"],
                        help="Sensibilidad del aplauso (0..1). Más bajo = más sensible.")
    parser.add_argument("--hf-ratio", type=float, default=DEFAULT_HF_RATIO,
                        help="Mínimo de agudos (0..1) para distinguir aplauso de tos/voz.")
    parser.add_argument("--max-clap-ms", type=float, default=cfg["max_clap_ms"],
                        help="Duración máxima de un aplauso en ms (más largo = tos/ruido).")
    parser.add_argument("--playlist", default=cfg["playlist_uri"],
                        help="URI/enlace de la playlist de Spotify a reproducir.")
    parser.add_argument("--no-shuffle", action="store_true",
                        help="Reproduce la playlist en orden, sin shuffle.")
    parser.add_argument("--calibrate", action="store_true",
                        help="Mide tus aplausos y ajusta la sensibilidad automáticamente.")
    parser.add_argument("--debug", action="store_true",
                        help="Muestra nivel y agudos para calibrar.")
    args = parser.parse_args()

    if args.calibrate:
        calibrate()
        return

    playlist_uri = normalize_playlist(args.playlist)
    shuffle = cfg["shuffle"] and not args.no_shuffle

    sustain = args.threshold * SUSTAIN_FACTOR
    max_clap_blocks = max(1, round(args.max_clap_ms / BLOCK_MS))

    state = {
        "last_clap": 0.0,    # timestamp del último aplauso válido
        "first_clap": 0.0,   # timestamp del primer aplauso de un par
        "muted_until": 0.0,  # cooldown tras disparar
        "run_len": 0,        # bloques consecutivos por encima de 'sustain'
        "run_peak": 0.0,     # pico máximo durante la racha actual
        "run_start": 0.0,    # inicio de la racha actual
    }

    def register_clap(t):
        """Registra un aplauso válido y dispara si es el segundo del par."""
        if (t - state["last_clap"]) < DEBOUNCE:
            return
        if state["first_clap"] and (t - state["first_clap"]) <= DOUBLE_WINDOW:
            if not args.debug:
                print("👏👏 doble aplauso detectado")
            wea_bakn_spotify(playlist_uri, shuffle)
            state["first_clap"] = 0.0
            state["muted_until"] = t + COOLDOWN
        else:
            state["first_clap"] = t
        state["last_clap"] = t

    def callback(indata, frames, time_info, status):
        now = time.monotonic()
        peak = float(np.abs(indata).max())
        active = peak >= sustain          # ¿hay sonido relevante en este bloque?

        if now < state["muted_until"]:
            state["run_len"] = 0          # no acumular durante el cooldown
            return

        if active:
            # Estamos dentro de una racha de sonido fuerte: acumular
            if state["run_len"] == 0:
                state["run_start"] = now
                state["run_peak"] = 0.0
            state["run_len"] += 1
            state["run_peak"] = max(state["run_peak"], peak)
        elif state["run_len"] > 0:
            # La racha acaba de terminar -> clasificar
            blocks, rpeak = state["run_len"], state["run_peak"]
            state["run_len"] = 0
            short = blocks <= max_clap_blocks                 # breve = aplauso
            strong = rpeak >= args.threshold                 # suficientemente fuerte
            hf_ok = args.hf_ratio <= 0.0 or hf_ratio(indata) >= args.hf_ratio
            is_clap = short and strong and hf_ok
            if args.debug:
                dur = blocks * BLOCK_MS
                tag = "👏 APLAUSO" if is_clap else ("🗣️ largo/tos" if strong else "ruido")
                print(f" pico:{rpeak:5.3f} dur:{dur:5.0f}ms ({blocks}b) -> {tag}", flush=True)
            if is_clap:
                register_clap(state["run_start"])

        if args.debug and active:
            bars = int(peak * 40)
            print(f"\r nivel:{peak:5.3f} {'█' * bars:<40}", end="", flush=True)

    print("🎧 Escuchando... aplaude DOS veces para reproducir tu playlist.")
    print(f"   (umbral={args.threshold}, dur.máx≈{args.max_clap_ms:.0f}ms, Ctrl+C para salir)")
    if args.debug:
        print("   [debug: cada sonido muestra su pico y duración; aplauso = breve]\n")

    try:
        with sd.InputStream(channels=1, samplerate=SAMPLERATE,
                            blocksize=BLOCKSIZE, callback=callback):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n👋 Hasta luego.")


if __name__ == "__main__":
    main()
