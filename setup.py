"""Empaqueta iClapp como .app de macOS con py2app.

    python setup.py py2app          # build de release en dist/iClapp.app

Genera un bundle de barra de menú (sin icono en el Dock) con el permiso de
micrófono declarado, para que macOS muestre el diálogo normal al iniciar.
"""

import glob

from setuptools import setup

APP = ["iclapp_app.py"]

# Localización del diálogo de permiso de micrófono: cada lproj/<lang>.lproj/
# InfoPlist.strings se copia a Contents/Resources/<lang>.lproj/ y macOS elige el
# que coincida con el idioma del sistema (cae al base/CFBundleDevelopmentRegion).
LANGS = ["en", "es", "pt", "fr", "de", "it"]
DATA_FILES = [
    (f"{lang}.lproj", glob.glob(f"lproj/{lang}.lproj/*.strings")) for lang in LANGS
]

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "icon.icns",
    # _sounddevice_data debe ir SIN comprimir: contiene libportaudio.dylib, y una
    # .dylib no se puede cargar desde dentro del zip (dlopen falla con errno=20).
    "packages": ["iclapp", "numpy", "sounddevice", "_sounddevice_data", "rumps"],
    "plist": {
        "CFBundleName": "iClapp",
        "CFBundleDisplayName": "iClapp",
        "CFBundleIdentifier": "com.iclapp.app",
        "CFBundleVersion": "1.1.1",
        "CFBundleShortVersionString": "1.1.1",
        # Idiomas que el bundle declara soportar + idioma base (fallback en inglés).
        "CFBundleDevelopmentRegion": "en",
        "CFBundleLocalizations": LANGS,
        # Sin icono en el Dock: vive en la barra de menú.
        "LSUIElement": True,
        # Texto base (fallback en inglés) del diálogo de permiso de micrófono;
        # se sobreescribe por idioma vía los InfoPlist.strings de cada .lproj.
        "NSMicrophoneUsageDescription":
            "iClapp listens to the microphone to detect your claps.",
    },
}

setup(
    app=APP,
    name="iClapp",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
