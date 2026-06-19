# 👏 iClap

Aplaude **dos veces** y tu Mac reproduce tu playlist de Spotify en shuffle.
Corre en segundo plano y arranca solo al iniciar sesión.

Funciona escuchando el micrófono y distinguiendo un aplauso (fuerte y **breve**)
de la voz o la tos (más largas). No graba ni envía nada: todo es local.

## Requisitos

- **macOS**
- **Python 3** (viene con macOS, o instálalo con `brew install python`)
- **Spotify de escritorio** instalado (la app, no solo la web)
- Un **micrófono** (el del MacBook sirve)

## Instalación rápida (un solo comando)

Pega esto en la Terminal y listo:

```bash
curl -fsSL https://raw.githubusercontent.com/papopelo/iClap/master/bootstrap.sh | bash
```

Clona iClap en `~/iClap` y deja el servicio cargado. (Si te falta `git` o
`python3`, macOS te ofrecerá instalar las *Command Line Tools*; acéptalo y
vuelve a correr el comando.)

## Instalación manual

```bash
git clone https://github.com/papopelo/iClap.git
cd iClap
./install.sh
```

El instalador crea el entorno, deja un `config.json` listo y carga el servicio.
Después haz estos tres pasos (te los recuerda al final):

1. **Pon tu playlist** en `config.json` (campo `playlist_uri`).
   Cópiala desde Spotify: clic derecho en la playlist → *Compartir* →
   *Copiar enlace*. Vale el enlace web o la URI (`spotify:playlist:...`).
2. **Calibra tus aplausos** (ajusta la sensibilidad a tu micro y tus manos):
   ```bash
   ./run.sh --calibrate
   ```
   Esto además dispara el diálogo de **permiso de micrófono** de macOS: acéptalo.
3. **Reinicia el servicio** para aplicar todo:
   ```bash
   launchctl kickstart -k gui/$(id -u)/com.iclap.detector
   ```

Listo: **aplaude dos veces** 👏👏 y suena tu playlist.

## Configuración (`config.json`)

| Campo          | Qué hace                                                        |
|----------------|----------------------------------------------------------------|
| `playlist_uri` | Tu playlist (URI `spotify:playlist:...` o enlace web).         |
| `threshold`    | Sensibilidad del aplauso (0..1). Más bajo = más sensible.      |
| `max_clap_ms`  | Duración máxima de un aplauso en ms (más largo = tos/ruido).   |
| `shuffle`      | `true` para reproducir al azar, `false` para orden de playlist.|

`threshold` y `max_clap_ms` se ajustan solos con `--calibrate`; no hace falta tocarlos a mano.

## Probar a mano

```bash
./run.sh              # modo normal (en primer plano)
./run.sh --debug      # muestra pico y duración de cada sonido para afinar
./run.sh --calibrate  # recalibra la sensibilidad
./run.sh --no-shuffle # reproduce en orden
./run.sh --playlist "https://open.spotify.com/playlist/XXXX"
```

## Logs y control del servicio

```bash
tail -f iclap.log                                     # ver actividad
launchctl kickstart -k gui/$(id -u)/com.iclap.detector  # reiniciar
./uninstall.sh                                        # quitar el servicio
```

## Problemas comunes

- **No detecta nada:** falta el permiso de micrófono. Corre `./run.sh --calibrate`
  desde Terminal y acepta el diálogo; luego reinicia el servicio. macOS entrega
  audio en silencio a procesos sin permiso (no se cae, pero nunca oye).
- **Detecta de más (con la tele, al hablar):** sube `threshold` o baja `max_clap_ms`,
  o simplemente vuelve a calibrar.
- **Detecta de menos:** baja `threshold` o vuelve a calibrar.
- **Spotify abre pero no suena:** asegúrate de tener la app de escritorio abierta
  y una sesión iniciada. Con cuenta gratuita Spotify mete anuncios y limita algunos
  saltos; con Premium va fino.
