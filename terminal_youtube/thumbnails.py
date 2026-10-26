"""Thumbnail downloading and on-disk cache (no UI code here)."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import CACHE_DIR


async def download_thumbnail(url: str | None) -> Path | None:
    """Download and cache a thumbnail, returning its local path."""

    if not url:
        return None

    parsed = urlparse(url)

    if parsed.scheme != "https":
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    filename = hashlib.sha256(url.encode()).hexdigest() + ".jpg"
    destination = CACHE_DIR / filename

    if destination.is_file() and destination.stat().st_size > 0:
        return destination

    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        if len(response.content) > 10 * 1024 * 1024:
            return None

        if not response.headers.get("content-type", "").startswith("image/"):
            return None

        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(response.content)
        temporary.replace(destination)

        return destination

    except (httpx.HTTPError, OSError):
        logging.exception("Thumbnail download failed")
        return None
