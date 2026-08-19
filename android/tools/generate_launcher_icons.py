#!/usr/bin/env python3
"""Generate safe-area GOAR launcher icon PNGs from the in-app monochrome mark."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app" / "src" / "main" / "res" / "drawable-nodpi" / "goar_logo.png"
RES = ROOT / "app" / "src" / "main" / "res"
SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}


def render(size: int) -> Image.Image:
    source = Image.open(SOURCE).convert("RGBA")
    mark_size = round(size * 0.72)
    mark = source.resize((mark_size, mark_size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    offset = (size - mark_size) // 2
    canvas.alpha_composite(mark, (offset, offset))
    return canvas


def main() -> None:
    for directory, size in SIZES.items():
        target = RES / directory
        target.mkdir(parents=True, exist_ok=True)
        image = render(size)
        for name in ("ic_launcher.png", "ic_launcher_round.png"):
            image.save(target / name, format="PNG", optimize=True)


if __name__ == "__main__":
    main()
