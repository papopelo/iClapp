"""Motor de detección de aplausos (numpy + sounddevice).

Misma lógica calibrada del proyecto original (aplauso = fuerte + breve; voz/tos
se descartan por durar más), ahora encapsulada en una clase reusable por el CLI
y por el .app, con selección de micrófono de entrada.
"""

import time

import numpy as np
import sounddevice as sd

# --- Parámetros fijos de captura ---------------------------------------------
SAMPLERATE = 44100        # Hz
BLOCKSIZE = 1024          # muestras por bloque (~23 ms)
BLOCK_MS = 1000.0 * BLOCKSIZE / SAMPLERATE
SUSTAIN_FACTOR = 0.5      # fracción del umbral para medir la "cola" del sonido
DEBOUNCE = 0.15           # s: tiempo mínimo entre dos aplausos
DOUBLE_WINDOW = 0.80      # s: ventana máxima entre aplauso 1 y 2
COOLDOWN = 5.0            # s: pausa tras disparar (evita re-disparo con la música)


def list_input_devices():
    """Devuelve [(nombre, index)] de los dispositivos con entrada de audio."""
    devices = []
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) > 0:
            devices.append((d["name"], i))
    return devices


def _device_index(name):
    """Resuelve un nombre de micrófono a su índice; None = por defecto."""
    if not name:
        return None
    for dev_name, idx in list_input_devices():
        if dev_name == name:
            return idx
    return None  # no encontrado: caer al dispositivo por defecto


class ClapEngine:
    """Escucha el micrófono y llama `on_double_clap()` al detectar 👏👏."""

    def __init__(self, on_double_clap, threshold=0.45, max_clap_ms=160,
                 input_device=None):
        self.on_double_clap = on_double_clap
        self.threshold = threshold
        self.max_clap_ms = max_clap_ms
        self.input_device = input_device
        self._stream = None
        self._state = None

    def _reset_state(self):
        self._state = {
            "last_clap": 0.0, "first_clap": 0.0, "muted_until": 0.0,
            "run_len": 0, "run_peak": 0.0, "run_start": 0.0,
        }

    def _register_clap(self, t):
        s = self._state
        if (t - s["last_clap"]) < DEBOUNCE:
            return
        if s["first_clap"] and (t - s["first_clap"]) <= DOUBLE_WINDOW:
            s["first_clap"] = 0.0
            s["muted_until"] = t + COOLDOWN
            try:
                self.on_double_clap()
            except Exception:
                pass
        else:
            s["first_clap"] = t
        s["last_clap"] = t

    def _callback(self, indata, frames, time_info, status):
        s = self._state
        sustain = self.threshold * SUSTAIN_FACTOR
        max_blocks = max(1, round(self.max_clap_ms / BLOCK_MS))
        now = time.monotonic()
        peak = float(np.abs(indata).max())

        if now < s["muted_until"]:
            s["run_len"] = 0
            return

        if peak >= sustain:
            if s["run_len"] == 0:
                s["run_start"] = now
                s["run_peak"] = 0.0
            s["run_len"] += 1
            s["run_peak"] = max(s["run_peak"], peak)
        elif s["run_len"] > 0:
            blocks, rpeak = s["run_len"], s["run_peak"]
            s["run_len"] = 0
            is_clap = blocks <= max_blocks and rpeak >= self.threshold
            if is_clap:
                self._register_clap(s["run_start"])

    def start(self):
        """Abre el stream de audio y empieza a escuchar."""
        if self._stream is not None:
            return
        self._reset_state()
        self._stream = sd.InputStream(
            channels=1, samplerate=SAMPLERATE, blocksize=BLOCKSIZE,
            device=_device_index(self.input_device), callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        """Cierra el stream y libera el micrófono."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    @property
    def running(self):
        return self._stream is not None
