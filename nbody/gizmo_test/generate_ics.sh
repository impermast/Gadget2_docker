#!/bin/bash
# generate_ics.sh — генерация ICs через GalIC + конвертация PartType1 -> PartType3
#
# Использование:
#   ./generate_ics.sh              # взять N_HALO из param файла
#   ./generate_ics.sh 300000       # обновить N_HALO в param файле и пересоздать ICs
#
# Ожидаемая структура:
#   /opt/GalIC/GalIC
#   /nbody/GalIC/halo_nfw_ics.param      или /nbody/GalIC/params/halo_nfw_ics.param
#   /nbody/scripts/convert_to_pt3.py
#
# Результат:
#   /nbody/gizmo_test/halo_<N>_sidm_ic.hdf5

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NBODY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

GALIC_BIN_DIR="/opt/GalIC"
GALIC_BIN="${GALIC_BIN_DIR}/GalIC"
GALIC_WORK_DIR="${NBODY_ROOT}/GalIC"
CONVERT_SCRIPT="${NBODY_ROOT}/scripts/convert_to_pt3.py"

PARAM_NAME="${PARAM_NAME:-halo_nfw_ics.param}"

if [[ -f "${GALIC_WORK_DIR}/params/${PARAM_NAME}" ]]; then
    PARAM_PATH="${GALIC_WORK_DIR}/params/${PARAM_NAME}"
else
    PARAM_PATH="${GALIC_WORK_DIR}/${PARAM_NAME}"
fi

if [[ ! -x "${GALIC_BIN}" ]]; then
    echo "[ERROR] GalIC binary not found or not executable: ${GALIC_BIN}"
    exit 1
fi

if [[ ! -f "${PARAM_PATH}" ]]; then
    echo "[ERROR] GalIC parameter file not found: ${PARAM_PATH}"
    exit 1
fi

if [[ ! -f "${CONVERT_SCRIPT}" ]]; then
    echo "[ERROR] Conversion script not found: ${CONVERT_SCRIPT}"
    exit 1
fi

export LD_LIBRARY_PATH="/opt/gsl/lib:/opt/fftw/lib:/usr/lib/x86_64-linux-gnu/hdf5/openmpi:${LD_LIBRARY_PATH:-}"

# --- N_HALO: либо из аргумента, либо читаем из param файла ---
if [[ $# -gt 1 ]]; then
    echo "[ERROR] Usage: $0 [N_HALO]"
    exit 1
fi

if [[ $# -eq 1 ]]; then
    N="$1"
    echo "[INFO] Setting N_HALO=${N} in ${PARAM_PATH}"
    sed -i -E "s/^([[:space:]]*N_HALO[[:space:]]+).*/\1${N}/" "${PARAM_PATH}"
else
    N="$(awk '/^[[:space:]]*N_HALO[[:space:]]+/ {print $2; exit}' "${PARAM_PATH}")"
    if [[ -z "${N}" ]]; then
        echo "[ERROR] Could not read N_HALO from ${PARAM_PATH}"
        exit 1
    fi
fi

# --- Читаем OutputDir и OutputFile из param файла ---
OUTPUT_DIR_RAW="$(awk '/^[[:space:]]*OutputDir[[:space:]]+/ {print $2; exit}' "${PARAM_PATH}")"
OUTPUT_FILE="$(awk '/^[[:space:]]*OutputFile[[:space:]]+/ {print $2; exit}' "${PARAM_PATH}")"

if [[ -z "${OUTPUT_DIR_RAW}" || -z "${OUTPUT_FILE}" ]]; then
    echo "[ERROR] Failed to read OutputDir or OutputFile from ${PARAM_PATH}"
    exit 1
fi

if [[ "${OUTPUT_DIR_RAW}" = /* ]]; then
    OUTPUT_DIR_ABS="${OUTPUT_DIR_RAW}"
else
    OUTPUT_DIR_ABS="${GALIC_WORK_DIR}/${OUTPUT_DIR_RAW}"
fi

mkdir -p "${OUTPUT_DIR_ABS}"

echo "[INFO] GalIC binary   : ${GALIC_BIN}"
echo "[INFO] GalIC work dir : ${GALIC_WORK_DIR}"
echo "[INFO] Param file     : ${PARAM_PATH}"
echo "[INFO] N_HALO         : ${N}"
echo "[INFO] Output dir     : ${OUTPUT_DIR_ABS}"
echo "[INFO] Output file    : ${OUTPUT_FILE}"

# --- Запускаем GalIC ---
echo "[INFO] Running GalIC..."
cd "${GALIC_WORK_DIR}"
"${GALIC_BIN}" "$(basename "${PARAM_PATH}")"

# --- Находим последний снапшот ---
SNAP="$(find "${OUTPUT_DIR_ABS}" -maxdepth 1 -type f -name "${OUTPUT_FILE}_*.hdf5" | sort | tail -n 1)"

if [[ -z "${SNAP}" ]]; then
    echo "[ERROR] No output snapshot found in ${OUTPUT_DIR_ABS}"
    exit 2
fi

echo "[INFO] Using snapshot: ${SNAP}"

# --- Конвертируем PartType1 -> PartType3 ---
OUTFILE="${SCRIPT_DIR}/halo_${N}_sidm_ic.hdf5"

python3 "${CONVERT_SCRIPT}" "${SNAP}" "${OUTFILE}"

echo "[INFO] Done. IC file: ${OUTFILE}"
echo "[INFO] Set in gizmo param:"
echo "       InitCondFile  $(basename "${OUTFILE}" .hdf5)"
