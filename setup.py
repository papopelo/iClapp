"""Empaqueta iClapp como .app de macOS con py2app.

    python setup.py py2app          # build de release en dist/iClapp.app

Genera un bundle de barra de menú (sin icono en el Dock) con el permiso de
micrófono declarado, para que macOS muestre el diálogo normal al iniciar.
"""

from setuptools import setup

APP = ["iclapp_app.py"]
DATA_FILES = []
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
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        # Sin icono en el Dock: vive en la barra de menú.
        "LSUIElement": True,
        # Texto del diálogo de permiso de micrófono.
        "NSMicrophoneUsageDescription":
            "iClapp escucha el micrófono para detectar tus aplausos.",
    },
}

setup(
    app=APP,
    name="iClapp",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
