# Terminal YouTube

Browse and watch YouTube from your terminal. Search videos, navigate a
responsive thumbnail grid, and play them in mpv, all from the keyboard and
without opening a browser.

Built with [Textual](https://github.com/Textualize/textual),
[textual-image](https://github.com/lnqs/textual-image),
[yt-dlp](https://github.com/yt-dlp/yt-dlp) and
[python-mpv](https://github.com/jaseg/python-mpv).

![screenshot](docs/screenshot.png)

## Features

- Search YouTube from inside the TUI
- Thumbnail grid that adapts its column count and image size to your terminal
- Infinite scroll: more results load as you near the bottom
- Thumbnails are cached locally for fast repeat searches
- Playback in mpv with YouTube-style quality (144p to 2160p) and speed controls

## Requirements

- Python 3.10 or newer
- [mpv](https://mpv.io) and libmpv
- A terminal that supports inline images (Kitty, WezTerm, iTerm2 or Sixel)
- A JavaScript runtime ([Deno](https://deno.com) or Node.js), which yt-dlp
  needs to resolve YouTube streams

On Debian/Ubuntu:

```bash
sudo apt install mpv libmpv2 nodejs
```

## Installation

```bash
git clone git@github.com:<your-username>/terminal-youtube.git
cd terminal-youtube
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run it from the project root:

```bash
python3 -m terminal_youtube
```

Type a search and press Enter. Press Esc to move from the search box to the
video grid.

### Controls

| Key | Action |
|---|---|
| Arrow keys | Move between videos |
| Enter | Play the selected video |
| Ctrl+L | Focus the search box |
| Esc | Return to the grid |
| Q | Quit |

### Inside mpv

| Key | Action |
|---|---|
| Ctrl+Up / Ctrl+Down | Quality up / down (reloads at the same timestamp) |
| `>` / `<` | Speed +0.25x / -0.25x |
| `[` `]` `{` `}` Backspace | Fine speed, halve/double, reset |
| Space, F, M | Pause, fullscreen, mute |

## Configuration

Settings such as column width, results per batch, quality list and default
quality live in [`terminal_youtube/config.py`](terminal_youtube/config.py).

## Project structure

```
terminal_youtube/
├── __main__.py     entry point
├── config.py       settings and paths
├── search.py       YouTube search (yt-dlp)
├── thumbnails.py   thumbnail download and cache
├── player.py       mpv playback, quality and speed keys
├── widgets.py      VideoCard widget
└── app.py          Textual app: layout, navigation, infinite scroll
```

## Troubleshooting

- **"Requested format is not available":** update yt-dlp
  (`pip install -U "yt-dlp[default]"`) and make sure a JavaScript runtime
  such as Node.js or Deno is installed.
- **Playback fails:** the status bar shows the error. Full details are in
  `~/.cache/terminal-youtube/app.log`.
- **`libmpv` not found:** install it (`sudo apt install libmpv2`).
- **`attempted relative import with no known parent package`:** run it as a
  module from the project root (`python3 -m terminal_youtube`), not as
  `python3 app.py`.
- **Thumbnails don't show:** your terminal may not support inline images. Try
  Kitty or WezTerm.

## Disclaimer

For personal use. Respect YouTube's Terms of Service.
