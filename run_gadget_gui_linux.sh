#!/bin/bash

HOST_PATH="/home/kds/sci/threebody/GadgetDocker/dockerData"

if [ -z "$DISPLAY" ]; then
    echo "WARNING: DISPLAY is not set. GUI applications may not work."
fi

if command -v xhost >/dev/null 2>&1; then
    xhost +local:root
fi

echo ">>> Running container with mounted folder..."

docker run -it --rm \
  --env DISPLAY=$DISPLAY \
  --volume "$HOST_PATH":/workspace/dockerData \
  --volume /tmp/.X11-unix:/tmp/.X11-unix \
  gadget2

if command -v xhost >/dev/null 2>&1; then
    xhost -local:root
fi
