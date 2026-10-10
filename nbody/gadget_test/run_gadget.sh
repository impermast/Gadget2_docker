#!/usr/bin/env bash
set -euo pipefail

# --- Configuration ---
DEFAULT_MAKEFILE="./Makefile"
DEFAULT_PARAMFILE="./lcdm_gas.param"
GADGET_DIR="${GADGET_HOME:-/opt/gadget-2.0.7}"
EXECUTABLE="Gadget2"

usage() {
    cat <<'EOF'
Usage: run_gadget.sh [Makefile path] [parameter file]

With no arguments, ./Makefile and ./lcdm_gas.param are used.
GADGET_HOME may be set to override the in-container source directory.
EOF
}

if [[ $# -eq 0 ]]; then
    MAKEFILE_SRC="$DEFAULT_MAKEFILE"
    PARAMFILE="$DEFAULT_PARAMFILE"
elif [[ $# -eq 2 ]]; then
    MAKEFILE_SRC="$1"
    PARAMFILE="$2"
else
    usage >&2
    exit 2
fi

if [[ ! -f "$MAKEFILE_SRC" ]]; then
    echo "[ERROR] Makefile not found: $MAKEFILE_SRC" >&2
    exit 2
fi

if [[ ! -f "$PARAMFILE" ]]; then
    echo "[ERROR] Parameter file not found: $PARAMFILE" >&2
    exit 2
fi

if [[ ! -d "$GADGET_DIR" || ! -f "$GADGET_DIR/Makefile" ]]; then
    echo "[ERROR] GADGET-2 source directory is not usable: $GADGET_DIR" >&2
    echo "        Expected GADGET_HOME/Makefile inside the container." >&2
    exit 3
fi

CALL_DIR="$(pwd -P)"
PARAM_SOURCE="$(realpath "$PARAMFILE")"
PARAM_BASENAME="$(basename "$PARAMFILE")"

echo "[INFO] Preparing GADGET-2 build in $GADGET_DIR..."
cp "$MAKEFILE_SRC" "$GADGET_DIR/Makefile"
cp "$PARAMFILE" "$GADGET_DIR/$PARAM_BASENAME"

echo "[INFO] Building Gadget2..."
make -C "$GADGET_DIR" clean
make -C "$GADGET_DIR"

echo "[INFO] Copying Gadget2 executable to $CALL_DIR..."
cp "$GADGET_DIR/$EXECUTABLE" "$CALL_DIR/"
if [[ "$PARAM_SOURCE" != "$CALL_DIR/$PARAM_BASENAME" ]]; then
    cp "$PARAMFILE" "$CALL_DIR/$PARAM_BASENAME"
fi

echo "[INFO] Running simulation with $PARAM_BASENAME"
mpirun --allow-run-as-root -np 1 "./$EXECUTABLE" "$PARAM_BASENAME"

echo "[INFO] Simulation completed successfully."
