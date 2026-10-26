"""mpv playback with YouTube-style quality and speed controls.

No Textual code here, so it can be used and tested on its own.
"""

from __future__ import annotations

import locale
import os
import sys
from pathlib import Path

import mpv

from .config import (
    DEFAULT_QUALITY,
    MAX_SPEED,
    MIN_SPEED,
    QUALITIES,
    SPEED_STEP,
)

# Remembered between videos during one session.
_quality_index = QUALITIES.index(DEFAULT_QUALITY)


def _format_for(height: int) -> str:
    return (
        f"bestvideo[height<={height}]+bestaudio/"
        f"best[height<={height}]/best"
    )


def play_with_mpv(webpage_url: str) -> None:
    """Play a YouTube page URL with libmpv, using mpv's yt-dlp integration.

    Keys inside the mpv window:
      Ctrl+Up / Ctrl+Down   quality up / down (reloads at current position)
      > / <                 speed +0.25x / -0.25x
      ] [  { }  Backspace   mpv defaults (+-10%, x2 / x0.5, reset)
    """
    global _quality_index

    # python-mpv requires the numeric locale to be "C".
    locale.setlocale(locale.LC_NUMERIC, "C")

    # Make sure the yt-dlp executable from this venv is found by mpv.
    bin_dir = str(Path(sys.executable).parent)
    if bin_dir not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

    errors: list[str] = []

    def on_log(level: str, component: str, message: str) -> None:
        if level in ("error", "fatal"):
            errors.append(f"{component}: {message.strip()}")

    player = mpv.MPV(
        ytdl=True,
        ytdl_format=_format_for(QUALITIES[_quality_index]),
        input_default_bindings=True,
        input_vo_keyboard=True,
        osc=True,
        force_window="yes",
        log_handler=on_log,
        loglevel="warn",
    )

    @player.event_callback("file-loaded")
    def _on_loaded(_event) -> None:
        # Clear the one-shot resume position used when changing quality.
        try:
            player.start = "none"
        except Exception:
            pass

    def change_quality(step: int) -> None:
        global _quality_index
        new_index = max(0, min(len(QUALITIES) - 1, _quality_index + step))

        if new_index == _quality_index:
            player.show_text(f"Quality: {QUALITIES[new_index]}p (limit)", 1500)
            return

        _quality_index = new_index
        height = QUALITIES[new_index]
        position = player.time_pos or 0

        player.show_text(f"Quality: {height}p ...", 3000)
        player.ytdl_format = _format_for(height)
        player.start = str(int(position))
        player.play(webpage_url)

    def change_speed(delta: float) -> None:
        speed = round(
            max(MIN_SPEED, min(MAX_SPEED, (player.speed or 1.0) + delta)),
            2,
        )
        player.speed = speed
        player.show_text(f"Speed: {speed}x", 1200)

    @player.on_key_press("ctrl+up")
    def _quality_up() -> None:
        change_quality(+1)

    @player.on_key_press("ctrl+down")
    def _quality_down() -> None:
        change_quality(-1)

    @player.on_key_press(">")
    def _speed_up() -> None:
        change_speed(+SPEED_STEP)

    @player.on_key_press("<")
    def _speed_down() -> None:
        change_speed(-SPEED_STEP)

    try:
        player.play(webpage_url)
        player.show_text(
            "Ctrl+Up/Down: quality   < >: speed   [ ]: fine speed", 4000
        )
        # wait_for_playback() would return when the file is replaced during a
        # quality change, so wait for the whole player to shut down instead.
        if hasattr(player, "wait_for_shutdown"):
            player.wait_for_shutdown()
        else:
            player.wait_for_playback()
    except mpv.ShutdownError:
        # Raised when the user closes the mpv window - this is normal.
        pass
    finally:
        try:
            player.terminate()
        except Exception:
            pass

    if errors:
        raise RuntimeError(errors[-1])
