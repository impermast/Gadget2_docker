#!/bin/bash
# generate_ic.sh — генерация ICs через GalIC + конвертация в PartType3 для SIDM
#
# Использование:
#   ./generate_ic.sh                    # N=100000 (из param файла)
#   ./generate_ic.sh 300000             # пересоздать с N=300000
#
# Результат: halo_<N>_sidm_ic.hdf5 в текущей директории

N=${1:-100000}
GALIC_DIR="/workspace/GalIC"
PARAM="halo_nfw_ics.param"
PARAM_PATH="$GALIC_DIR/$PARAM"

export LD_LIBRARY_PATH="/workspace/gsl/lib:/workspace/fftw/lib:/usr/lib/x86_64-linux-gnu/hdf5/openmpi:${LD_LIBRARY_PATH}"

# --- Обновляем N_HALO если передан аргумент ---
if [ "$#" -eq 1 ]; then
    echo "[INFO] Setting N_HALO=$N in $PARAM"
    sed -i "s/^N_HALO.*/N_HALO         $N/" "$PARAM_PATH"
fi

# --- Читаем OutputDir и OutputFile из param файла ---
OUTPUT_DIR=$(grep -E '^OutputDir' "$PARAM_PATH" | awk '{print $2}')
OUTPUT_FILE=$(grep -E '^OutputFile' "$PARAM_PATH" | awk '{print $2}')

echo "[INFO] GalIC output: $GALIC_DIR/$OUTPUT_DIR/${OUTPUT_FILE}_006.hdf5"

# --- Запускаем GalIC ---
echo "[INFO] Running GalIC with N_HALO=$N..."
cd "$GALIC_DIR"
./GalIC "$PARAM"
if [ $? -ne 0 ]; then
    echo "[ERROR] GalIC failed."
    exit 1
fi

# --- Находим последний снапшот ---
SNAP=$(ls -t "$GALIC_DIR/$OUTPUT_DIR/${OUTPUT_FILE}"_*.hdf5 2>/dev/null | head -1)
if [ -z "$SNAP" ]; then
    echo "[ERROR] No output snapshot found in $GALIC_DIR/$OUTPUT_DIR/"
    exit 2
fi
echo "[INFO] Using snapshot: $SNAP"

# --- Конвертируем PartType1 → PartType3 ---
OUTFILE="$OLDPWD/halo_${N}_sidm_ic.hdf5"
cd "$OLDPWD"
python3 /workspace/scripts/convert_to_pt3.py "$SNAP" "$OUTFILE"
if [ $? -ne 0 ]; then
    echo "[ERROR] Conversion failed."
    exit 3
fi

echo "[INFO] Done. IC file: $OUTFILE"
echo "[INFO] Update InitCondFile in your .param to: $(basename $OUTFILE .hdf5)"
