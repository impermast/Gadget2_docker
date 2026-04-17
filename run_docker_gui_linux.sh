#!/bin/bash
set -euo pipefail

DEFAULT_CONTAINER_NAME="gadget-gizmo"
CONTAINER_NAME=""
IMAGE_NAME="${IMAGE_NAME:-gadget-gizmo:ver2}"
RECREATE=0

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case "$key" in
        --name)
            if [[ -n "${2:-}" ]]; then
                CONTAINER_NAME="$2"
                shift 2
            else
                echo "Error: Argument for --name is missing"
                exit 1
            fi
            ;;
        --image)
            if [[ -n "${2:-}" ]]; then
                IMAGE_NAME="$2"
                shift 2
            else
                echo "Error: Argument for --image is missing"
                exit 1
            fi
            ;;
        --recreate)
            RECREATE=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--name CONTAINER_NAME] [--image IMAGE_NAME] [--recreate]"
            exit 1
            ;;
    esac
done

# If no name was provided, use the default
if [[ -z "$CONTAINER_NAME" ]]; then
    CONTAINER_NAME="$DEFAULT_CONTAINER_NAME"
fi

# Repository root = directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST_PATH="${SCRIPT_DIR}/nbody"
CONTAINER_PATH="/nbody"

if [[ ! -d "$HOST_PATH" ]]; then
    echo "Error: Host directory '$HOST_PATH' does not exist."
    echo "Expected repository layout:"
    echo "  ${SCRIPT_DIR}/nbody"
    exit 1
fi

if [[ -z "${DISPLAY:-}" ]]; then
    echo "WARNING: DISPLAY is not set. GUI applications may not work."
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "Error: docker command not found."
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo ">>> Docker daemon is not running. Starting it..."
    if command -v systemctl >/dev/null 2>&1; then
        sudo systemctl start docker
    else
        echo "Error: Docker daemon is not running and systemctl is unavailable."
        exit 1
    fi
fi

cleanup_xhost() {
    if command -v xhost >/dev/null 2>&1; then
        xhost -local:root >/dev/null 2>&1 || true
    fi
}

# Allow X server access for container root
if command -v xhost >/dev/null 2>&1; then
    xhost +local:root >/dev/null 2>&1 || true
    trap cleanup_xhost EXIT
fi

container_id="$(docker ps -a -q -f name=^/${CONTAINER_NAME}$)"

if [[ -n "$container_id" ]]; then
    existing_mount="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "'"$CONTAINER_PATH"'"}}{{.Source}}{{end}}{{end}}' "$CONTAINER_NAME" 2>/dev/null || true)"
    existing_image="$(docker inspect -f '{{.Config.Image}}' "$CONTAINER_NAME" 2>/dev/null || true)"

    if [[ "$RECREATE" -eq 1 || "$existing_mount" != "$HOST_PATH" || "$existing_image" != "$IMAGE_NAME" ]]; then
        echo ">>> Recreating container '$CONTAINER_NAME'..."
        docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
        container_id=""
    fi
fi

if [[ -z "$container_id" ]]; then
    echo ">>> Creating and starting new container '$CONTAINER_NAME'..."
    docker run -it \
        --name "$CONTAINER_NAME" \
        --env DISPLAY="${DISPLAY:-}" \
        --env QT_X11_NO_MITSHM=1 \
        --workdir "$CONTAINER_PATH" \
        --volume "$HOST_PATH":"$CONTAINER_PATH" \
        --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
        "$IMAGE_NAME"
else
    if docker ps -q -f name=^/${CONTAINER_NAME}$ >/dev/null 2>&1 && [[ -n "$(docker ps -q -f name=^/${CONTAINER_NAME}$)" ]]; then
        echo ">>> Container '$CONTAINER_NAME' is already running. Opening shell..."
        docker exec -it "$CONTAINER_NAME" bash
    else
        echo ">>> Container '$CONTAINER_NAME' already exists. Starting it..."
        docker start -ai "$CONTAINER_NAME"
    fi
fi
