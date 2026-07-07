"""Uploaded image storage in Postgres (bytea).

Images are optimized with Pillow and stored as bytes so they survive Vercel's
read-only filesystem and persist across deploys. Served via a Flask route with
long cache headers. If volume grows, swap the store for object storage (e.g.
Vercel Blob) while keeping the /media/img/<id> URL shape stable.
"""

import hashlib
import io
import logging

import psycopg2
from PIL import Image, UnidentifiedImageError

from database import get_db

logger = logging.getLogger(__name__)

MAX_WIDTH = 1600
WEBP_QUALITY = 82
# Reject anything above this after decode fails / animated giant, etc.
MAX_SOURCE_BYTES = 12 * 1024 * 1024  # 12 MB
ALLOWED_INPUT = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _new_id(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:20]


def optimize(raw: bytes):
    """Return (optimized_bytes, content_type). Falls back to original on GIF
    (to preserve animation) or if re-encoding fails."""
    try:
        img = Image.open(io.BytesIO(raw))
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError("Unsupported or corrupt image file") from e

    # Preserve animated GIFs untouched.
    if getattr(img, "is_animated", False):
        return raw, "image/gif"

    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 0))
        img = Image.alpha_composite(background, img).convert("RGB")
    else:
        img = img.convert("RGB")

    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        img = img.resize((MAX_WIDTH, round(img.height * ratio)), Image.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
    return out.getvalue(), "image/webp"


class ImageStore:
    @staticmethod
    def save(raw: bytes, filename=None, content_type=None):
        """Optimize and persist an uploaded image. Returns its id, or None."""
        if not raw:
            return None
        if len(raw) > MAX_SOURCE_BYTES:
            raise ValueError("Image too large (max 12 MB)")
        if content_type and content_type not in ALLOWED_INPUT:
            raise ValueError(f"Unsupported image type: {content_type}")

        data, out_type = optimize(raw)
        image_id = _new_id(data)

        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO images (id, filename, content_type, data, byte_size)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    image_id,
                    filename,
                    out_type,
                    psycopg2.Binary(data),
                    len(data),
                ),
            )
            conn.commit()
            return image_id
        except psycopg2.Error as e:
            logger.error(f"Error saving image: {e}")
            conn.rollback()
            return None

    @staticmethod
    def get(image_id):
        """Return (bytes, content_type) or None."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return None
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT data, content_type FROM images WHERE id = %s", (image_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return bytes(row[0]), row[1]
        except psycopg2.Error as e:
            logger.error(f"Error fetching image {image_id}: {e}")
            return None
