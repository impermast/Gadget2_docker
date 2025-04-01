#!/bin/bash

CONFIG_FILE="docker_mount_path.conf"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: File '$CONFIG_FILE' not found. Please create it and specify the path to mount."
    exit 1
fi

HOST_PATH=$(cat "$CONFIG_FILE")

if [ ! -d "$HOST_PATH" ]; then
    echo "ERROR: Path '$HOST_PATH' does not exist."
    exit 1
fi

if [ -z "$DISPLAY" ]; then
    echo "WARNING: DISPLAY is not set. GUI applications may not work."
fi

if command -v xhost >/dev/null 2>&1; then
    xhost +local:root
fi

echo ">>> Running container with mounted folder..."

docker run -it --rm \
  --env DISPLAY=$DISPLAY \
  --volume "$HOST_PATH":/workspace \
  --volume /tmp/.X11-unix:/tmp/.X11-unix \
  gadget-gui

if command -v xhost >/dev/null 2>&1; then
    xhost -local:root
fi
