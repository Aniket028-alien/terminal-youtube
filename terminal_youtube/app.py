"""The Textual application: layout, navigation and infinite scroll."""

from __future__ import annotations

import asyncio
import logging

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, VerticalScroll
from textual.widgets import Input, Label

from .config import (
    CARD_CHROME,
    CELL_ASPECT,
    GRID_GUTTER,
    INITIAL_RESULTS,
    MAX_COLUMNS,
    MIN_CARD_WIDTH,
    RESULTS_INCREMENT,
    SCROLL_LOAD_MARGIN,
    TEXT_ROWS,
)
from .player import play_with_mpv
from .search import search_videos
from .widgets import VideoCard


class TerminalYouTube(App[None]):

    TITLE = "Terminal YouTube"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+l", "focus_search", "Search"),
        ("escape", "focus_grid", "Browse"),
    ]

    CSS = """
    Screen {
        background: rgba(0, 0, 0, 0.12);
        color: white;
    }

    #header {
        height: 3;
        padding: 0 2;
        background: rgba(0, 0, 0, 0.15);
    }

    #logo {
        width: 23;
        color: #ff3333;
        text-style: bold;
        content-align: left middle;
    }

    #search {
        width: 1fr;
        margin: 0 2;
        background: rgba(40, 40, 40, 0.65);
        color: white;
        border: round #777777;
    }

    #status {
        height: 1;
        padding-left: 2;
        color: #cccccc;
        background: transparent;
    }

    #results-scroll {
        height: 1fr;
        background: transparent;
        padding: 1 2;
    }

    #video-grid {
        width: 100%;
        height: auto;
        grid-size: 4;
        grid-columns: 1fr;
        grid-rows: 16;
        grid-gutter: 1 1;
        background: transparent;
    }

    #footer {
        height: 1;
        padding-left: 2;
        color: #cccccc;
        background: transparent;
    }
    """

    def __init__(self) -> None:
        super().__init__()

        self.search_text = ""
        self.videos: list[dict] = []
        self.cards: list[VideoCard] = []

        self.loaded_limit = 0
        self.is_loading = False
        self.exhausted = False

        self.columns = 4
        self.image_height = 8

    def compose(self) -> ComposeResult:
        with Horizontal(id="header"):
            yield Label("▶ Terminal YouTube", id="logo")
            yield Input(
                placeholder="Search YouTube...",
                id="search",
            )

        yield Label("Enter a search query to get started.", id="status")

        with VerticalScroll(id="results-scroll"):
            yield Grid(id="video-grid")

        yield Label(
            "↑ ↓ ← → Navigate     Enter Play     Ctrl+L Search     Q Quit",
            id="footer",
        )

    async def on_mount(self) -> None:
        self.query_one("#search", Input).focus()

        scroll = self.query_one("#results-scroll", VerticalScroll)
        self.watch(scroll, "scroll_y", self._on_scroll_change)

        self.call_after_refresh(self.relayout)

    # ---------------- Responsive layout ----------------

    def on_resize(self) -> None:
        self.call_after_refresh(self.relayout)

    def relayout(self) -> None:
        """Pick column count + card/image size from the terminal width."""

        scroll = self.query_one("#results-scroll", VerticalScroll)
        grid = self.query_one("#video-grid", Grid)

        # Usable width: scroll width minus horizontal padding (4) and
        # the vertical scrollbar.
        usable = scroll.size.width - 4 - scroll.scrollbar_size_vertical

        if usable < MIN_CARD_WIDTH:
            usable = max(usable, MIN_CARD_WIDTH)

        columns = max(
            1,
            min(
                MAX_COLUMNS,
                (usable + GRID_GUTTER) // (MIN_CARD_WIDTH + GRID_GUTTER),
            ),
        )

        card_width = (usable - (columns - 1) * GRID_GUTTER) // columns
        inner_width = max(8, card_width - 4)   # border + horizontal padding

        # 16:9 thumbnail, corrected for non-square terminal cells.
        image_height = max(4, round(inner_width * 9 / 16 / CELL_ASPECT))
        card_height = image_height + TEXT_ROWS + CARD_CHROME

        self.columns = columns
        self.image_height = image_height

        grid.styles.grid_size_columns = columns
        grid.set_styles(f"grid-rows: {card_height};")

        for card in self.cards:
            card.thumbnail_widget.styles.height = image_height

        self.refresh(layout=True)
        self.call_after_refresh(self._fill_screen_if_needed)

    def _fill_screen_if_needed(self) -> None:
        """Keep loading until the content is taller than the viewport."""

        scroll = self.query_one("#results-scroll", VerticalScroll)

        if (
            self.search_text
            and not self.is_loading
            and not self.exhausted
            and scroll.max_scroll_y <= SCROLL_LOAD_MARGIN
        ):
            self.run_worker(self.load_more(), exclusive=False)

    def _on_scroll_change(self, value: float) -> None:
        scroll = self.query_one("#results-scroll", VerticalScroll)

        if (
            self.search_text
            and not self.is_loading
            and not self.exhausted
            and scroll.max_scroll_y - value <= SCROLL_LOAD_MARGIN
        ):
            self.run_worker(self.load_more(), exclusive=False)

    # ---------------- Search ----------------

    @on(Input.Submitted, "#search")
    async def submit_search(self, event: Input.Submitted) -> None:
        query = event.value.strip()

        if query:
            await self.start_search(query)

    async def start_search(self, query: str) -> None:
        self.search_text = query
        self.videos.clear()
        self.cards.clear()

        self.loaded_limit = 0
        self.exhausted = False

        grid = self.query_one("#video-grid", Grid)
        await grid.remove_children()

        self.query_one("#results-scroll", VerticalScroll).scroll_home(
            animate=False
        )

        self.query_one("#status", Label).update(
            f"Searching for {query!r}..."
        )

        await self.load_more()

        self.focus_first_card()

    async def load_more(self) -> None:
        if self.is_loading or self.exhausted or not self.search_text:
            return

        self.is_loading = True

        try:
            new_limit = (
                INITIAL_RESULTS
                if self.loaded_limit == 0
                else self.loaded_limit + RESULTS_INCREMENT
            )

            self.query_one("#status", Label).update(
                f"Loading results... ({len(self.videos)} available)"
            )

            found = await asyncio.to_thread(
                search_videos,
                self.search_text,
                new_limit,
            )

            known_ids = {
                video["id"]
                for video in self.videos
                if video.get("id")
            }

            added = [
                video
                for video in found
                if video.get("id") and video["id"] not in known_ids
            ]

            self.loaded_limit = new_limit

            if not added:
                self.exhausted = True
            else:
                self.videos.extend(added)

                grid = self.query_one("#video-grid", Grid)
                new_cards = []

                for video in added:
                    card = VideoCard(
                        video,
                        len(self.cards),
                        self.image_height,
                    )
                    self.cards.append(card)
                    new_cards.append(card)

                await grid.mount(*new_cards)

                # Thumbnails download in the background so cards show at once.
                for card in new_cards:
                    self.run_worker(card.load_thumbnail(), exclusive=False)

            self.query_one("#status", Label).update(
                f"{len(self.videos)} videos loaded"
                + (" · No more results found" if self.exhausted else "")
            )

        except Exception:
            logging.exception("Search failed")
            self.query_one("#status", Label).update(
                "Search failed. Check your connection and app.log."
            )

        finally:
            self.is_loading = False

        # If the screen is still not full (big terminal), keep going.
        self.call_after_refresh(self._fill_screen_if_needed)

    # ---------------- Focus / navigation ----------------

    def focus_first_card(self) -> None:
        if self.cards:
            self.cards[0].focus()

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_focus_grid(self) -> None:
        self.focus_first_card()

    async def on_key(self, event) -> None:
        search = self.query_one("#search", Input)

        if search.has_focus:
            return

        if not self.cards:
            return

        focused = self.focused

        if not isinstance(focused, VideoCard):
            return

        index = focused.index
        new_index = index
        columns = self.columns

        if event.key == "left":
            new_index = max(0, index - 1)

        elif event.key == "right":
            new_index = min(len(self.cards) - 1, index + 1)

        elif event.key == "up":
            new_index = max(0, index - columns)

        elif event.key == "down":
            new_index = index + columns

            if new_index >= len(self.cards) - columns and not self.exhausted:
                await self.load_more()

            new_index = min(new_index, len(self.cards) - 1)

        elif event.key == "enter":
            await self.play_video(focused.video)
            event.stop()
            return

        else:
            return

        if new_index < len(self.cards):
            self.cards[new_index].focus()
            self.cards[new_index].scroll_visible()

        event.stop()

    # ---------------- Playback ----------------

    async def play_video(self, video: dict) -> None:
        url = video.get("url")

        if not url:
            self.query_one("#status", Label).update(
                "This result does not have a usable video URL."
            )
            return

        self.query_one("#status", Label).update(
            f"Preparing playback: {video['title']}"
        )

        try:
            await asyncio.to_thread(play_with_mpv, url)

            self.query_one("#status", Label).update(
                f"Finished playback: {video['title']}"
            )

        except Exception as error:
            logging.exception("Playback failed")
            message = " ".join(str(error).split())[:140] or type(error).__name__
            self.query_one("#status", Label).update(
                f"Playback failed: {message}"
            )
