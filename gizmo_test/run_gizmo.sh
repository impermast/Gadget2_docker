#!/bin/bash

# --- Default configuration ---
DEFAULT_CONFIG_FILE="./Config.sh"
DEFAULT_MAKEFILE="./Makefile"
DEFAULT_PARAMFILE="./gizmo.param"
GIZMO_DIR="/workspace/gizmo-public"
EXECUTABLE="GIZMO"

# --- Get the calling directory ---
CALL_DIR="$(pwd)"

# --- Argument handling ---
if [ "$#" -eq 0 ]; then
    echo "[INFO] No arguments passed. Using defaults."
    CONFIG_FILE_SRC="$DEFAULT_CONFIG_FILE"
    MAKEFILE_SRC="$DEFAULT_MAKEFILE"
    PARAMFILE_SRC="$DEFAULT_PARAMFILE"
elif [ "$#" -eq 3 ]; then
    CONFIG_FILE_SRC="$1"
    MAKEFILE_SRC="$2"
    PARAMFILE_SRC="$3"
else
    echo "[ERROR] Usage: $0 [Config.sh path] [Makefile path] [Parameter file path]"
    echo "[ERROR] Or provide no arguments to use defaults."
    exit 1
fi

# --- File checks ---
if [ ! -f "$CONFIG_FILE_SRC" ]; then
    echo "[ERROR] Config file not found: $CONFIG_FILE_SRC"
    exit 2
fi
if [ ! -f "$MAKEFILE_SRC" ]; then
    echo "[ERROR] Makefile not found: $MAKEFILE_SRC"
    exit 3
fi
if [ ! -f "$PARAMFILE_SRC" ]; then
    echo "[ERROR] Parameter file not found: $PARAMFILE_SRC"
    exit 4
fi

# --- Copy files to GIZMO directory ---
echo "[INFO] Preparing GIZMO build..."
cp "$CONFIG_FILE_SRC" "$GIZMO_DIR/Config.sh"
# REMOVED: cp "$MAKEFILE_SRC" "$GIZMO_DIR/Makefile" - This was overwriting the original GIZMO Makefile
PARAM_BASENAME=$(basename "$PARAMFILE_SRC")
cp "$PARAMFILE_SRC" "$GIZMO_DIR/$PARAM_BASENAME"

# --- Extract CFLAGS_EXTRA and LIBS_EXTRA from the wrapper Makefile ---
# This parses the Makefile in gizmo_test to get the build flags.
# It's important to use the Makefile from gizmo_test as the source of truth for these flags.
CFLAGS_VAL=$(grep -E '^CFLAGS\s*=' "$MAKEFILE_SRC" | cut -d'=' -f2- | xargs)
INCL_VAL=$(grep -E '^INCL\s*=' "$MAKEFILE_SRC" | cut -d'=' -f2- | xargs)
CFLAGS_EXTRA_VAL="$CFLAGS_VAL $INCL_VAL"

LIBS_VAL=$(grep -E '^LIBS\s*=' "$MAKEFILE_SRC" | cut -d'=' -f2- | xargs)
LIBS_EXTRA_VAL="$LIBS_VAL"

# --- Compile ---
echo "[INFO] Building GIZMO in $GIZMO_DIR..."
# Now, we execute the original GIZMO Makefile (Makefile.gizmo) directly
# and pass the extracted flags.
make -C "$GIZMO_DIR" clean && make -C "$GIZMO_DIR" -f Makefile.gizmo CFLAGS_EXTRA="$CFLAGS_EXTRA_VAL" LIBS_EXTRA="$LIBS_EXTRA_VAL" -j$(nproc)
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
mpirun --allow-run-as-root -n 1 .//"$EXECUTABLE" "$PARAM_BASENAME"
if [ $? -ne 0 ]; then
    echo "[ERROR] GIZMO terminated with an error."
else
    echo "[INFO] Simulation completed successfully."
fi

echo "[INFO] Script finished."
