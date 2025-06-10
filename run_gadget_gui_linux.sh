#!/bin/bash

CONTAINER_NAME="gadget2"
HOST_PATH="/home/kds/sci/threebody/GadgetDocker/dockerData"

if [ -z "$DISPLAY" ]; then
    echo "WARNING: DISPLAY is not set. GUI applications may not work."
fi

# Разрешаем доступ X-сервера
if command -v xhost >/dev/null 2>&1; then
    xhost +local:root
fi

# Проверка: существует ли контейнер
if [ "$(docker ps -a -q -f name=^/${CONTAINER_NAME}$)" ]; then
    echo ">>> Container already exists. Starting it..."
    docker start -ai "$CONTAINER_NAME"
else
    echo ">>> Creating and starting new container..."
    docker run -it \
        --name "$CONTAINER_NAME" \
        --env DISPLAY=$DISPLAY \
        --volume "$HOST_PATH":/workspace/dockerData \
        --volume /tmp/.X11-unix:/tmp/.X11-unix \
        gadget2
fi

# Удаляем разрешение после запуска (опционально)
if command -v xhost >/dev/null 2>&1; then
    xhost -local:root
fi
