"""mpv playback with YouTube-style quality and speed controls.

No Textual code here, so it can be used and tested on its own.
"""

from __future__ import annotations

import locale
import logging
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

    # Intel's Vulkan driver prints warnings straight to the terminal, which
    # garbles the TUI. Hide Vulkan so mpv uses OpenGL instead.
    os.environ.setdefault("VK_LOADER_DRIVERS_DISABLE", "*")

    errors: list[str] = []

    def on_log(level: str, component: str, message: str) -> None:
        text = message.strip()
        logging.warning("mpv [%s] %s: %s", level, component, text)
        if level in ("error", "fatal"):
            errors.append(f"{component}: {text}")

    # Optional override, e.g. TY_MPV_VO=x11 for Docker on macOS/WSL.
    extra_options = {"gpu_api": os.environ.get("TY_MPV_GPU_API", "opengl")}
    if os.environ.get("TY_MPV_VO"):
        extra_options["vo"] = os.environ["TY_MPV_VO"]

    player = mpv.MPV(
        ytdl=True,
        ytdl_format=_format_for(QUALITIES[_quality_index]),
        input_default_bindings=True,
        input_vo_keyboard=True,
        osc=True,
        force_window="yes",
        log_handler=on_log,
        loglevel="warn",
        **extra_options,
    )

    state = {"seen_active": False, "switching": False}

    @player.event_callback("file-loaded")
    def _on_loaded(_event) -> None:
        state["switching"] = False
        # Clear the one-shot resume position used when changing quality.
        try:
            player.start = "none"
        except Exception:
            pass

    @player.property_observer("idle-active")
    def _on_idle(_name, idle) -> None:
        # mpv is idle before loading (ignore), busy while loading/playing,
        # and idle again when the video ended OR failed to load. In both
        # cases close the window so the TUI regains control and can show
        # the error instead of leaving a blank "Drop files here" window.
        if idle is False:
            state["seen_active"] = True
        elif idle and state["seen_active"] and not state["switching"]:
            player.command("quit")

    def change_quality(step: int) -> None:
        global _quality_index
        new_index = max(0, min(len(QUALITIES) - 1, _quality_index + step))

        if new_index == _quality_index:
            player.show_text(f"Quality: {QUALITIES[new_index]}p (limit)", 1500)
            return

        _quality_index = new_index
        height = QUALITIES[new_index]
        position = player.time_pos or 0

        state["switching"] = True
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
            "Loading video (can take up to 30 s)...   "
            "Ctrl+Up/Down: quality   < >: speed",
            8000,
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
