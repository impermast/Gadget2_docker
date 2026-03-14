#!/bin/bash
#run_gizmo.sh

# --- Default configuration ---
DEFAULT_CONFIG_FILE="./Config.sh"
DEFAULT_PARAMFILE="./gizmo.param"
GIZMO_DIR="/workspace/gizmo-public"
EXECUTABLE="GIZMO"
NPROC_DEFAULT = 1

# --- Get the calling directory ---
CALL_DIR="$(pwd)"

# --- Argument handling ---
if [ "$#" -eq 0 ]; then
    echo "[INFO] No arguments passed. Using defaults."
    CONFIG_FILE_SRC="$DEFAULT_CONFIG_FILE"
    PARAMFILE_SRC="$DEFAULT_PARAMFILE"
elif [ "$#" -eq 2 ]; then
    CONFIG_FILE_SRC="$1"
    PARAMFILE_SRC="$2"
elif [ "$#" -eq 3 ]; then
    CONFIG_FILE_SRC="$1"
    PARAMFILE_SRC="$2"
    NPROC="$3"
else
    echo "[ERROR] Usage: $0 [Config.sh path] [Parameter file path]"
    echo "[ERROR] Or provide no arguments to use defaults."
    exit 1
fi

# --- File checks ---
if [ ! -f "$CONFIG_FILE_SRC" ]; then
    echo "[ERROR] Config file not found: $CONFIG_FILE_SRC"
    exit 2
fi
if [ ! -f "$PARAMFILE_SRC" ]; then
    echo "[ERROR] Parameter file not found: $PARAMFILE_SRC"
    exit 4
fi
if [ ! -d "$GIZMO_DIR" ]; then
    echo "[ERROR] GIZMO directory not found: $GIZMO_DIR"
    exit 6
fi

# --- Copy files to GIZMO directory ---
echo "[INFO] Preparing GIZMO build..."
cp "$CONFIG_FILE_SRC" "$GIZMO_DIR/Config.sh"
PARAM_BASENAME=$(basename "$PARAMFILE_SRC")
cp "$PARAMFILE_SRC" "$GIZMO_DIR/$PARAM_BASENAME"

# --- Compile ---
echo "[INFO] Building GIZMO in $GIZMO_DIR..."
make -C "$GIZMO_DIR" clean
make -C "$GIZMO_DIR" -j"$(nproc)"
if [ $? -ne 0 ]; then
    echo "[ERROR] Compilation failed."
    exit 5
fi

# --- Copy executable back ---
echo "[INFO] Copying GIZMO executable to working directory..."
cp "$GIZMO_DIR/$EXECUTABLE" "$CALL_DIR/"

# --- Run simulation ---
echo "[INFO] Running simulation with $PARAM_BASENAME"
cd "$CALL_DIR"
export LD_LIBRARY_PATH="/workspace/gsl/lib:/workspace/fftw/lib:/usr/lib/x86_64-linux-gnu/hdf5/openmpi:${LD_LIBRARY_PATH}"
mpirun --allow-run-as-root -n "$NPROC" ./"$EXECUTABLE" "$PARAM_BASENAME"
if [ $? -ne 0 ]; then
    echo "[ERROR] GIZMO terminated with an error."
else
    echo "[INFO] Simulation completed successfully."
fi

echo "[INFO] Script finished."
