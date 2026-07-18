"""Conversión de imágenes subidas a JPEG.

WhatsApp Cloud API solo acepta imágenes JPEG/PNG (no webp ni heic). Para que las
fotos lleguen SIEMPRE, normalizamos todo lo que sube el corredor a JPEG, y de paso
las achicamos a un tamaño razonable (Meta limita a 5 MB)."""
from __future__ import annotations

import io
import logging
from pathlib import Path

log = logging.getLogger("images")

try:  # soporte HEIC (fotos de iPhone), si el wheel está disponible
    import pillow_heif  # type: ignore
    pillow_heif.register_heif_opener()
except Exception:  # noqa: BLE001
    pass

try:
    from PIL import Image
    _PIL = True
except Exception:  # noqa: BLE001
    _PIL = False


def to_jpeg(data: bytes, dest: Path, max_side: int = 1600, quality: int = 85) -> bool:
    """Convierte los bytes de una imagen (webp/png/jpg/heic/…) a JPEG en `dest`.
    Devuelve True si se guardó bien."""
    if not _PIL:
        log.error("Pillow no está instalado; no se puede convertir la imagen.")
        return False
    try:
        img = Image.open(io.BytesIO(data))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side))
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, format="JPEG", quality=quality, optimize=True)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo convertir la imagen: %s", exc)
        return False
