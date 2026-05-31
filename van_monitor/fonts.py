"""Load fonts for the dashboard (Figma uses Inter Bold; we use DejaVu on the Pi)."""

from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FONT_CANDIDATES = (
    _REPO_ROOT / "fonts" / "DejaVuSans-Bold.ttf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/Library/Fonts/Arial Bold.ttf"),
)


def load_bold_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a bold sans font at the given pixel size, or fall back to default."""
    for path in _FONT_CANDIDATES:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()
