"""Load bundled Inter fonts for the dashboard (Figma Main screen v3)."""

from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FONTS_DIR = _REPO_ROOT / "fonts"

_INTER_BOLD = _FONTS_DIR / "Inter-Bold.ttf"
_INTER_MEDIUM_ITALIC = _FONTS_DIR / "Inter-MediumItalic.ttf"

_FALLBACK_BOLD = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
)
_FALLBACK_ITALIC = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSans-Oblique.ttf"),
)


def _load_truetype(candidates: tuple[Path, ...], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def load_bold_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Inter Bold — zone labels, hero values, body metrics."""
    return _load_truetype((_INTER_BOLD, *_FALLBACK_BOLD), size)


def load_caption_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Inter Medium Italic — right-aligned capacity / max captions."""
    return _load_truetype((_INTER_MEDIUM_ITALIC, *_FALLBACK_ITALIC, *_FALLBACK_BOLD), size)
