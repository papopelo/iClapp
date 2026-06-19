"""Reproduce una URL en el servicio correcto según su dominio.

- Spotify      -> AppleScript a la app (play + shuffle; track/álbum/playlist).
- Apple Music  -> abre la URL en la app Music (+ shuffle por AppleScript).
- YouTube Music-> abre la URL en el navegador (básico; sin control de shuffle).
"""

import subprocess
import sys


def classify(url):
    """Devuelve 'spotify', 'apple', 'youtube' o None según la URL."""
    u = url.strip().lower()
    if u.startswith("spotify:") or "open.spotify.com" in u:
        return "spotify"
    if "music.apple.com" in u or u.startswith("itmss:") or u.startswith("itms:"):
        return "apple"
    if "music.youtube.com" in u or "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    return None


def to_spotify_uri(url):
    """'https://open.spotify.com/playlist/ABC?si=x' -> 'spotify:playlist:ABC'."""
    url = url.strip()
    if url.startswith("spotify:"):
        return url
    if "open.spotify.com" in url:
        path = url.split("open.spotify.com/", 1)[1].split("?", 1)[0]
        # Maneja enlaces con prefijo de idioma: /intl-es/playlist/ID
        parts = [p for p in path.strip("/").split("/") if p]
        if len(parts) >= 2 and parts[0].startswith("intl-"):
            parts = parts[1:]
        if len(parts) >= 2:
            return f"spotify:{parts[0]}:{parts[1]}"
    return url


def _osascript(script):
    subprocess.run(["osascript", "-e", script], check=True,
                   capture_output=True, text=True)


def _play_spotify(url, shuffle):
    uri = to_spotify_uri(url)
    shuffle_setup = "set shuffling to true" if shuffle else "set shuffling to false"
    shuffle_jump = "next track\n        delay 0.2" if shuffle else ""
    _osascript(f'''
    if application "Spotify" is not running then
        tell application "Spotify" to activate
        delay 1.5
    end if
    tell application "Spotify"
        {shuffle_setup}
        play track "{uri}"
        delay 0.4
        {shuffle_jump}
        if player state is not playing then play
    end tell
    ''')


def _play_apple(url, shuffle):
    # Abrir la URL hace que la app Music la cargue y empiece a reproducir.
    subprocess.run(["open", url], check=True)
    if shuffle:
        # Pequeña espera y activamos shuffle en la app Music.
        _osascript('''
        delay 1.5
        tell application "Music"
            try
                set shuffle enabled to true
            end try
        end tell
        ''')


def _play_youtube(url, shuffle):
    # Sin app nativa: abrimos en el navegador por defecto. El autoplay y el
    # shuffle dependen del navegador/YouTube; es el modo más básico.
    subprocess.run(["open", url], check=True)


def play(url, shuffle=True):
    """Reproduce `url` en el servicio que corresponda.

    Devuelve (ok, mensaje). No lanza excepción: reporta el error en el mensaje.
    """
    service = classify(url)
    if service is None:
        return False, "URL no reconocida (usa Spotify, Apple Music o YouTube Music)."
    try:
        if service == "spotify":
            _play_spotify(url, shuffle)
            return True, "🎸 Spotify" + (" (shuffle)" if shuffle else "")
        if service == "apple":
            _play_apple(url, shuffle)
            return True, "🍎 Apple Music" + (" (shuffle)" if shuffle else "")
        if service == "youtube":
            _play_youtube(url, shuffle)
            return True, "▶️ YouTube Music (en el navegador)"
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or "").strip() or str(e)
        return False, f"Error al reproducir: {detail}"
    return False, "Servicio no soportado."


if __name__ == "__main__":
    # Prueba rápida: python -m iclapp.players "<url>"
    ok, msg = play(sys.argv[1], shuffle="--no-shuffle" not in sys.argv)
    print(msg)
    sys.exit(0 if ok else 1)
