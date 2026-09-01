"""Derive assets/icon.ico from assets/icon.png.

`assets/icon.png` is the master logo and is never overwritten by this script — an earlier
version generated the PNG from code, which would silently replace a designed logo with a
drawing. `assets/icon.svg` is the hand-authored vector twin, kept in step by hand.

`flet build` reads icon.png for the executable; the Windows taskbar needs a real .ico, which
window_icon.py attaches to the live window when running from source.
"""
from pathlib import Path

from PIL import Image

SOURCE = Path("assets/icon.png")
TARGET = Path("assets/icon.ico")
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

if not SOURCE.is_file():
    raise SystemExit(f"{SOURCE} is missing; it is the master logo and cannot be regenerated here.")

logo = Image.open(SOURCE).convert("RGBA")
# Trim the transparent margin so the small taskbar sizes are not mostly empty space.
box = logo.getbbox()
if box:
    logo = logo.crop(box)
side = max(logo.size)
square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
square.paste(logo, ((side - logo.width) // 2, (side - logo.height) // 2))

square.save(TARGET, sizes=SIZES)
print(f"{SOURCE} -> {TARGET}")
print(f"  source {Image.open(SOURCE).size}, trimmed to {logo.size}, square {square.size}")
print(f"  sizes {SIZES}")
