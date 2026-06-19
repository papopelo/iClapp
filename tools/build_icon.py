"""Compone icon.icns de iClap a partir del .icon de Icon Composer.

Replica el diseño: fondo degradado morado con forma de icono de macOS
(rejilla Big Sur) + el símbolo de aplauso centrado.

    python tools/build_icon.py [tamaño_símbolo_px]   # genera un PNG de 1024
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSET = ROOT / "iClap.icon" / "Assets" / "aplaudir 2.png"

SIZE = 1024
RECT = 824          # rejilla Big Sur: rect redondeado de 824 en lienzo de 1024
RADIUS = 185
# Fondo: degradado del morado base de icon.json (srgb 0.505,0.261,1.0).
TOP = (157, 108, 255)
BOTTOM = (110, 48, 235)


def gradient():
    img = Image.new("RGB", (SIZE, SIZE))
    d = ImageDraw.Draw(img)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        d.line([(0, y), (SIZE, y)], fill=tuple(
            int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)))
    return img


def rounded_mask():
    m = Image.new("L", (SIZE, SIZE), 0)
    off = (SIZE - RECT) // 2
    ImageDraw.Draw(m).rounded_rectangle(
        [off, off, off + RECT, off + RECT], radius=RADIUS, fill=255)
    return m


def compose(symbol_px):
    """Devuelve la imagen del icono compuesta a 1024×1024 (RGBA)."""
    mask = rounded_mask()
    icon = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    icon.paste(gradient(), (0, 0), mask)

    sym = Image.open(ASSET).convert("RGBA")
    sym = sym.crop(sym.getbbox())
    f = symbol_px / max(sym.size)
    sym = sym.resize((round(sym.width * f), round(sym.height * f)), Image.LANCZOS)
    icon.alpha_composite(sym, ((SIZE - sym.width) // 2, (SIZE - sym.height) // 2))

    # Recortar todo a la forma redondeada (que nada se salga del squircle).
    icon.putalpha(Image.composite(icon.getchannel("A"),
                                  Image.new("L", (SIZE, SIZE), 0), mask))
    return icon


def build_icns(symbol_px, out):
    """Compone y genera un .icns con todos los tamaños (vía iconutil)."""
    master = compose(symbol_px)
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "icon.iconset"
        iconset.mkdir()
        for s in sizes:
            img = master.resize((s, s), Image.LANCZOS)
            if s <= 512:
                img.save(iconset / f"icon_{s}x{s}.png")          # 1x
            if s >= 32:
                img.save(iconset / f"icon_{s // 2}x{s // 2}@2x.png")  # 2x
        subprocess.run(["iconutil", "-c", "icns", str(iconset),
                        "-o", str(out)], check=True)
    print(f"✅ {out}  (símbolo {symbol_px}px)")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "icns"
    if arg == "icns":
        px = int(sys.argv[2]) if len(sys.argv) > 2 else 560
        build_icns(px, ROOT / "icon.icns")
    else:  # vista previa: tamaño en px
        px = int(arg)
        compose(px).save(ROOT / f"preview_{px}.png")
        print(f"✅ preview_{px}.png")
