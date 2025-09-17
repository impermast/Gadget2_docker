#!/bin/bash

DEFAULT_CONTAINER_NAME="gadget-gizmo"
CONTAINER_NAME=""
IMAGE_NAME="gadget-gizmo:main"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --name)
        if [ -n "$2" ]; then
            CONTAINER_NAME="$2"
            shift # past argument
            shift # past value
        else
            echo "Error: Argument for --name is missing"
            exit 1
        fi
        ;; 
        *)
        echo "Unknown option: $1"
        exit 1
        ;; 
    esac
done

# If no name was provided, use the default
if [ -z "$CONTAINER_NAME" ]; then
    CONTAINER_NAME="$DEFAULT_CONTAINER_NAME"
fi

HOST_PATH="$(pwd)/dockerData"

if [ -z "$DISPLAY" ]; then
    echo "WARNING: DISPLAY is not set. GUI applications may not work."
fi

# Разрешаем доступ X-сервера
if command -v xhost >/dev/null 2>&1; then
    xhost +local:root
fi

# Проверка: существует ли контейнер
if [ "$(docker ps -a -q -f name=^/${CONTAINER_NAME}$)" ]; then
    echo ">>> Container '$CONTAINER_NAME' already exists. Starting it..."
    docker start -ai "$CONTAINER_NAME"
else
    echo ">>> Creating and starting new container '$CONTAINER_NAME'..."
    docker run -it \
        --name "$CONTAINER_NAME" \
        --env DISPLAY=$DISPLAY \
        --volume "$HOST_PATH":/workspace/dockerData \
        --volume /tmp/.X11-unix:/tmp/.X11-unix \
        "$IMAGE_NAME"
fi

# Удаляем разрешение после запуска (опционально)
if command -v xhost >/dev/null 2>&1; then
    xhost -local:root
fi