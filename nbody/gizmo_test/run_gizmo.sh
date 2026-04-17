#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$SCRIPT_DIR"
GIZMO_SRC="/opt/gizmo-public"
BUILD_DIR="$GIZMO_SRC"
OUTPUT_DIR="${WORK_DIR}/output"

CONFIG_FILE="${WORK_DIR}/Config_cdm_sidm.sh"
PARAM_FILE="${WORK_DIR}/gizmo_cdm.param"
RUN_SCRIPT_NAME="$(basename "$0")"

mkdir -p "$OUTPUT_DIR"

if [[ ! -d "$GIZMO_SRC" ]]; then
    echo "Error: GIZMO source directory not found: $GIZMO_SRC"
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

if [[ ! -f "$PARAM_FILE" ]]; then
    echo "Error: Parameter file not found: $PARAM_FILE"
    exit 1
fi

echo "=== GIZMO run script ==="
echo "Script       : $RUN_SCRIPT_NAME"
echo "Work dir     : $WORK_DIR"
echo "GIZMO source : $GIZMO_SRC"
echo "Config file  : $CONFIG_FILE"
echo "Param file   : $PARAM_FILE"
echo "Output dir   : $OUTPUT_DIR"
echo

cd "$BUILD_DIR"

# Подкладываем пользовательский Config.sh
cp "$CONFIG_FILE" Config.sh

# Если у тебя есть свой Makefile в gizmo_test, раскомментируй:
# cp "${WORK_DIR}/Makefile" Makefile

echo "=== Cleaning previous build ==="
make clean || true

echo "=== Building GIZMO ==="
make -j"$(nproc)"

echo "=== Preparing parameter file ==="
TMP_PARAM="${WORK_DIR}/.gizmo_run.param"
cp "$PARAM_FILE" "$TMP_PARAM"

# Если в параметрах есть OutputDir, можно автоматически переписать:
if grep -q '^OutputDir' "$TMP_PARAM"; then
    sed -i "s|^OutputDir.*|OutputDir  ${OUTPUT_DIR}/|" "$TMP_PARAM"
fi

echo "=== Running GIZMO ==="
mpirun --allow-run-as-root -np 1 ./GIZMO "$TMP_PARAM"

echo
echo "=== Done ==="
echo "Results are expected in: $OUTPUT_DIR"
