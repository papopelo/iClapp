"""Ventana de Preferencias (Tkinter).

Se ejecuta como proceso aparte (`python -m iclap.prefs`) para no chocar con el
loop de eventos de la barra de menú y para tener el micrófono libre al calibrar.
Al guardar, escribe la config y cierra; la app recarga al detectar el cierre.
"""

import queue
import threading
import tkinter as tk
from tkinter import ttk

from . import config
from .calibrate import measure, params_from
from .engine import list_input_devices

DEFAULT_LABEL = "Dispositivo por defecto"


class Prefs:
    def __init__(self, root):
        self.root = root
        self.cfg = config.load()
        self.events = queue.Queue()
        self._calibrating = False

        root.title("iClap — Preferencias")
        root.resizable(False, False)
        frm = ttk.Frame(root, padding=16)
        frm.grid(sticky="nsew")

        # --- Micrófono ---
        ttk.Label(frm, text="🎙️  Micrófono de entrada").grid(
            row=0, column=0, columnspan=2, sticky="w")
        self.devices = [(DEFAULT_LABEL, None)] + list_input_devices()
        names = [n for n, _ in self.devices]
        self.mic_var = tk.StringVar(value=self._current_mic_name())
        self.mic_menu = ttk.Combobox(frm, textvariable=self.mic_var, values=names,
                                     state="readonly", width=38)
        self.mic_menu.grid(row=1, column=0, columnspan=2, sticky="we", pady=(2, 12))

        # --- URL ---
        ttk.Label(frm, text="🔗  URL a reproducir (Spotify / Apple Music / "
                            "YouTube Music)").grid(
            row=2, column=0, columnspan=2, sticky="w")
        self.url_var = tk.StringVar(value=self.cfg.get("url", ""))
        ttk.Entry(frm, textvariable=self.url_var, width=42).grid(
            row=3, column=0, columnspan=2, sticky="we", pady=(2, 4))
        ttk.Label(frm, text="Soporta canción, álbum o playlist (pega el enlace).",
                  foreground="#888").grid(row=4, column=0, columnspan=2, sticky="w")

        self.shuffle_var = tk.BooleanVar(value=self.cfg.get("shuffle", True))
        ttk.Checkbutton(frm, text="Reproducir en shuffle (Spotify / Apple Music)",
                        variable=self.shuffle_var).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(8, 12))

        # --- Calibración ---
        ttk.Separator(frm, orient="horizontal").grid(
            row=6, column=0, columnspan=2, sticky="we", pady=4)
        cal = ttk.Frame(frm)
        cal.grid(row=7, column=0, columnspan=2, sticky="we", pady=(8, 0))
        self.cal_btn = ttk.Button(cal, text="🎚️  Calibrar aplausos",
                                  command=self.start_calibration)
        self.cal_btn.grid(row=0, column=0, sticky="w")
        self.cal_status = ttk.Label(
            cal, text=f"Actual: umbral {self.cfg['threshold']}, "
                      f"{self.cfg['max_clap_ms']} ms", foreground="#888")
        self.cal_status.grid(row=0, column=1, sticky="w", padx=10)

        # --- Guardar / Cerrar ---
        btns = ttk.Frame(frm)
        btns.grid(row=8, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(btns, text="Cancelar", command=root.destroy).grid(row=0, column=0)
        ttk.Button(btns, text="Guardar", command=self.save).grid(
            row=0, column=1, padx=(8, 0))

        root.after(100, self._drain_events)

    def _current_mic_name(self):
        saved = self.cfg.get("input_device")
        if not saved:
            return DEFAULT_LABEL
        for n, _ in list_input_devices():
            if n == saved:
                return saved
        return DEFAULT_LABEL

    # --- Calibración en hilo (la UI se actualiza vía cola) ---
    def start_calibration(self):
        if self._calibrating:
            return
        self._calibrating = True
        self.cal_btn.config(state="disabled")
        self.cal_status.config(text="Aplaude 5 veces, una a una…", foreground="#0a0")
        device = None if self.mic_var.get() == DEFAULT_LABEL else self.mic_var.get()
        threading.Thread(target=self._calibrate_worker, args=(device,),
                         daemon=True).start()

    def _calibrate_worker(self, device):
        def on_clap(i, n, peak, dur):
            self.events.put(("progress", (i, n)))
        try:
            claps = measure(n=5, input_device=device, on_clap=on_clap)
            self.events.put(("done", params_from(claps)))
        except Exception as e:  # noqa: BLE001
            self.events.put(("error", str(e)))

    def _drain_events(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "progress":
                    i, n = data
                    self.cal_status.config(text=f"👏 {i}/{n} capturados…")
                elif kind == "done":
                    self._finish_calibration(data)
                elif kind == "error":
                    self.cal_status.config(
                        text=f"Error: {data}", foreground="#c00")
                    self.cal_btn.config(state="normal")
                    self._calibrating = False
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)

    def _finish_calibration(self, params):
        self._calibrating = False
        self.cal_btn.config(state="normal")
        if params is None:
            self.cal_status.config(
                text="Pocos aplausos. Revisa el micrófono y reintenta.",
                foreground="#c00")
            return
        threshold, max_clap_ms = params
        config.save({"threshold": threshold, "max_clap_ms": max_clap_ms})
        self.cfg["threshold"] = threshold
        self.cfg["max_clap_ms"] = max_clap_ms
        self.cal_status.config(
            text=f"✅ Calibrado: umbral {threshold}, {max_clap_ms} ms",
            foreground="#0a0")

    def save(self):
        mic = None if self.mic_var.get() == DEFAULT_LABEL else self.mic_var.get()
        config.save({
            "url": self.url_var.get().strip(),
            "shuffle": self.shuffle_var.get(),
            "input_device": mic,
        })
        self.root.destroy()


def main():
    root = tk.Tk()
    Prefs(root)
    root.mainloop()


if __name__ == "__main__":
    main()
