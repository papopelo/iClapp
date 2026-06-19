"""Punto de entrada del .app (py2app).

El mismo ejecutable sirve para la app de barra de menú y para la ventana de
Preferencias: se distingue por la variable de entorno ICLAPP_MODE, que la app
fija al lanzar Preferencias como subproceso.
"""

import os


def run():
    mode = os.environ.get("ICLAPP_MODE")
    if mode == "prefs":
        from iclapp.prefs import main
    else:
        from iclapp.app import main
    main()


if __name__ == "__main__":
    run()
