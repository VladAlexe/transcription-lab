"""Derive every icon the application ships from the one master artwork.

`assets/icon.png` is the master and is never written by this script. It is a wide render
with the mark sitting on its own backdrop, which is the right thing for a picture and the
wrong thing for an icon: at 16 pixels a 1536x1024 frame is mostly backdrop with a smudge in
the middle. So everything else here is derived from a square crop around the mark.

  assets/icon_mark.png     the square crop, 1024x1024 — what the interface and the build use
  assets/icon_windows.png  the same at 512, which `flet build` puts on the executable
  assets/icon.ico          multi-size, attached to the live window by window_icon.py
  assets/icon.svg          the crop embedded in a vector wrapper

The crop is stated as fractions of the master rather than found automatically. The backdrop
is a smooth vignette, so nothing separates it from the artwork by tone or by saturation
alone — every automatic attempt either kept the whole frame or cut the glow off the mark.
Four numbers, checked by eye once, are the honest way to say where the mark is.
"""
import base64
from pathlib import Path

from PIL import Image

SOURCE = Path("assets/icon.png")
MARK = Path("assets/icon_mark.png")
WINDOWS = Path("assets/icon_windows.png")
ICO = Path("assets/icon.ico")
SVG = Path("assets/icon.svg")

# Centre of the mark and the side of the square around it, as fractions of the master.
CENTRE_X, CENTRE_Y, SIDE = 0.527, 0.500, 0.74
MASTER_SIDE = 1024
WINDOWS_SIDE = 512
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def square(image: Image.Image) -> Image.Image:
    """The master cropped to a square around the mark, at the master icon size."""
    width, height = image.size
    side = int(height * SIDE)
    left = int(width * CENTRE_X) - side // 2
    top = int(height * CENTRE_Y) - side // 2
    box = (max(0, left), max(0, top), min(width, left + side), min(height, top + side))
    return image.crop(box).resize((MASTER_SIDE, MASTER_SIDE), Image.LANCZOS)


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"{SOURCE} is missing; it is the master logo and cannot be regenerated here.")
    master = Image.open(SOURCE).convert("RGBA")
    mark = square(master)
    mark.save(MARK)
    mark.resize((WINDOWS_SIDE, WINDOWS_SIDE), Image.LANCZOS).save(WINDOWS)
    mark.save(ICO, sizes=ICO_SIZES)
    # The master is a raster render, so there is no vector twin to keep in step any more.
    # The SVG carries the same crop rather than a redrawing that would drift away from it.
    # The 512 copy, not the 1024 one: a vector wrapper around a raster is already a
    # compromise, and half a megabyte of base64 in a repository is a worse one.
    encoded = base64.b64encode(WINDOWS.read_bytes()).decode("ascii")
    SVG.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{MASTER_SIDE}" height="{MASTER_SIDE}" viewBox="0 0 {MASTER_SIDE} {MASTER_SIDE}">'
        f'<image width="{MASTER_SIDE}" height="{MASTER_SIDE}" '
        f'xlink:href="data:image/png;base64,{encoded}"/></svg>\n', encoding="utf-8")
    print(f"{SOURCE} {master.size} -> square crop {mark.size}")
    for path in (MARK, WINDOWS, ICO, SVG):
        print(f"  {path}  {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
