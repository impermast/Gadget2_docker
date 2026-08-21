#!/bin/bash
# run_sidm20.sh — запуск SIDM σ=20 для dwarf карлика (N=10⁶, v200=30, c=15)
# Запускается внутри Docker контейнера
set -euo pipefail

RUN_NAME="sidm20_dwarf_N1e6_v30_c15"
IC_FILE="/nbody/ics/dwarf_N1e6/dwarf_N1e6.hdf5"

# Проверка IC
if [[ ! -f "$IC_FILE" ]]; then
    echo "[ERROR] IC file not found: $IC_FILE"
    echo "Сначала выполни: bash /nbody/scripts/generate_ics.sh --config /nbody/ics/dwarf_N1e6.json"
    exit 1
fi

# Создаём run-директорию
BASE_DIR="/nbody/runs"
RUN_DIR="${BASE_DIR}/${RUN_NAME}"
mkdir -p "${RUN_DIR}/configs"
mkdir -p "${RUN_DIR}/output"
mkdir -p "${RUN_DIR}/plots"

# Копируем Config.sh
cp /nbody/gizmo_test/Config_cdm_sidm.sh "${RUN_DIR}/configs/Config.sh"

# Копируем и патрим .param
PARAM_SRC="/nbody/gizmo_test/gizmo_sidm20.param"
cp "$PARAM_SRC" "${RUN_DIR}/.gizmo_run.param"
cp "$PARAM_SRC" "${RUN_DIR}/configs/"

# Патчим IC и Output
sed -i "s|^InitCondFile.*|InitCondFile  ${IC_FILE%.hdf5}|" "${RUN_DIR}/.gizmo_run.param"
sed -i "s|^OutputDir.*|OutputDir  ${RUN_DIR}/output/|"   "${RUN_DIR}/.gizmo_run.param"

# Убедимся что σ=20
sed -i "s|^DM_InteractionCrossSection.*|DM_InteractionCrossSection    20.0|" "${RUN_DIR}/.gizmo_run.param"

# Настраиваем TimeMax на быстрый тест: 2 Gyr (единицы = 1 кпк/км/с ≈ 0.978 Gyr)
# TimeMax=2.0 = ~2 Gyr
sed -i "s|^TimeMax[[:space:]]*.*|TimeMax     2.0|" "${RUN_DIR}/.gizmo_run.param"

echo "[INFO] Run directory: ${RUN_DIR}"
echo "[INFO] IC: ${IC_FILE}"
echo "[INFO] Config: ${RUN_DIR}/configs/Config.sh"
echo "[INFO] Param: ${RUN_DIR}/.gizmo_run.param"

# Проверяем GIZMO бинарник
GIZMO_BIN="/opt/gizmo-public/GIZMO"
if [[ ! -f "$GIZMO_BIN" ]]; then
    echo "[INFO] Building GIZMO..."
    cp "${RUN_DIR}/configs/Config.sh" /opt/gizmo-public/Config.sh
    cd /opt/gizmo-public && make clean 2>/dev/null && make -j\$(nproc) 2>&1 | tail -5
    cd /nbody
    if [[ ! -f "$GIZMO_BIN" ]]; then
        echo "[ERROR] Build failed!"
        exit 1
    fi
    md5sum "${RUN_DIR}/configs/Config.sh" | cut -d' ' -f1 > /opt/gizmo-public/.last_build_config.md5
fi

echo "[INFO] Binary: ${GIZMO_BIN}"

# Запускаем
echo "[INFO] Starting simulation..."
cd "${RUN_DIR}"
mpirun --allow-run-as-root -np 4 "$GIZMO_BIN" ".gizmo_run.param" 2>&1 | tee run.log
SIM_STATUS=$?

echo "[INFO] Simulation exit code: $SIM_STATUS"

# Визуализация
LAST_SNAP=$(ls -t "${RUN_DIR}/output"/snapshot_*.hdf5 2>/dev/null | head -1)
if [[ -n "$LAST_SNAP" ]]; then
    echo "[INFO] Last snapshot: $LAST_SNAP"
    python3 /nbody/scripts/check_snapshot.py "$LAST_SNAP" 3 2>&1 | tee "${RUN_DIR}/snapshot_check.txt"
    echo "[INFO] Check snapshot done"
else
    echo "[WARN] No snapshots found"
fi

echo "[INFO] DONE. Run: ${RUN_DIR}"