"""Reusable Textual widgets."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label
from textual_image.widget import Image as TerminalImage

from .thumbnails import download_thumbnail


class VideoCard(Vertical):
    """One selectable thumbnail card."""

    can_focus = True

    DEFAULT_CSS = """
    VideoCard {
        height: 100%;
        width: 100%;
        padding: 0 1;
        border: round transparent;
        background: rgba(0, 0, 0, 0.12);
        overflow: hidden hidden;
    }

    VideoCard:focus {
        border: round #ff3333;
        background: rgba(100, 30, 30, 0.45);
    }

    VideoCard TerminalImage {
        width: 100%;
        height: 8;
    }

    VideoCard .video-title {
        width: 100%;
        height: 2;
        color: white;
        text-style: bold;
    }

    VideoCard .video-channel {
        width: 100%;
        height: 1;
        color: #c0c0c0;
    }
    """

    def __init__(self, video: dict, index: int, image_height: int) -> None:
        super().__init__(id=f"video-{index}")
        self.video = video
        self.index = index
        self.thumbnail_widget = TerminalImage()
        self.thumbnail_widget.styles.height = image_height

    def compose(self) -> ComposeResult:
        yield self.thumbnail_widget
        yield Label(
            self.video["title"],
            classes="video-title",
            markup=False,
        )
        yield Label(
            self.video["channel"],
            classes="video-channel",
            markup=False,
        )

    async def load_thumbnail(self) -> None:
        path = await download_thumbnail(self.video.get("thumbnail_url"))

        if path and self.is_mounted:
            self.thumbnail_widget.image = str(path)
