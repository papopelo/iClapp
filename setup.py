"""Empaqueta iClap como .app de macOS con py2app.

    python setup.py py2app          # build de release en dist/iClap.app

Genera un bundle de barra de menú (sin icono en el Dock) con el permiso de
micrófono declarado, para que macOS muestre el diálogo normal al iniciar.
"""

from setuptools import setup

APP = ["iclap_app.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "packages": ["iclap", "numpy", "sounddevice", "rumps"],
    "plist": {
        "CFBundleName": "iClap",
        "CFBundleDisplayName": "iClap",
        "CFBundleIdentifier": "com.iclap.app",
        "CFBundleVersion": "0.2.0",
        "CFBundleShortVersionString": "0.2.0",
        # Sin icono en el Dock: vive en la barra de menú.
        "LSUIElement": True,
        # Texto del diálogo de permiso de micrófono.
        "NSMicrophoneUsageDescription":
            "iClap escucha el micrófono para detectar tus aplausos.",
    },
}

setup(
    app=APP,
    name="iClap",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
