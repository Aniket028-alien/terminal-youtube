#!/usr/bin/env bash
# Loads the Terminal YouTube image (first time only) and runs it.
# Usage: ./run-terminal-youtube.sh [path/to/terminal-youtube.tar.gz]
set -eu

TARBALL="${1:-terminal-youtube.tar.gz}"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

if [ "$(id -u)" != "1000" ]; then
  echo "Warning: your user ID is $(id -u), not 1000."
  echo "Video or sound may not work. Ask the sender for a rebuilt image."
fi

if ! docker image inspect terminal-youtube >/dev/null 2>&1; then
  echo "Loading image from $TARBALL (first run only)..."
  docker load < "$TARBALL"
fi

# Let the container draw its video window on your desktop.
xhost +SI:localuser:"$(id -un)" >/dev/null

# Use the GPU if there is one.
DRI=()
[ -e /dev/dri ] && DRI=(--device /dev/dri)

docker run -it --rm \
  --security-opt label=disable \
  -e DISPLAY -e TERM -e COLORTERM \
  -e PULSE_SERVER=unix:/run/user/1000/pulse/native \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "$RUNTIME_DIR/pulse/native":/run/user/1000/pulse/native \
  -v yt-cache:/home/app/.cache/terminal-youtube \
  "${DRI[@]}" \
  terminal-youtube
