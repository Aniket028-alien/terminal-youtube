"""YouTube search through yt-dlp (no UI code here)."""

from __future__ import annotations

import yt_dlp


def search_videos(query: str, limit: int = 10) -> list[dict]:
    """Search YouTube and normalize results for the UI."""

    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        results = ydl.extract_info(
            f"ytsearch{limit}:{query}",
            download=False,
        )

    videos = []

    for item in results.get("entries") or []:
        if not item:
            continue

        video_id = item.get("id")
        video_url = item.get("webpage_url") or item.get("url")

        if video_url and not str(video_url).startswith(("http://", "https://")):
            if video_id:
                video_url = f"https://www.youtube.com/watch?v={video_id}"

        if not video_url and video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Prefer a real 16:9 thumbnail. Some flat-extraction thumbnails are
        # tall/cropped banners, so use the standard i.ytimg.com URL when we
        # have the ID.
        thumbnail_url = None
        if video_id:
            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
        else:
            thumbnails = item.get("thumbnails") or []
            best = max(
                thumbnails,
                key=lambda image: image.get("width") or 0,
                default=None,
            )
            thumbnail_url = best.get("url") if best else None

        videos.append(
            {
                "id": video_id,
                "url": video_url,
                "title": item.get("title") or "Untitled",
                "channel": item.get("channel") or "Unknown channel",
                "duration": item.get("duration"),
                "thumbnail_url": thumbnail_url,
            }
        )

    return videos
