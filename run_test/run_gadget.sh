#!/bin/bash

# --- Конфигурация по умолчанию ---
DEFAULT_MAKEFILE="./galaxy.Makefile"
DEFAULT_PARAMFILE="./galaxy.param"
GADGET_DIR="/workspace/Gadget-2.0.7/Gadget2"
EXECUTABLE="Gadget2"

# --- Определяем рабочую директорию вызова скрипта ---
CALL_DIR="$(pwd)"

# --- Обработка аргументов ---
if [ "$#" -eq 0 ]; then
    echo "[INFO] No arguments passed. Using defaults:"
    MAKEFILE_SRC="$DEFAULT_MAKEFILE"
    PARAMFILE="$DEFAULT_PARAMFILE"
elif [ "$#" -eq 2 ]; then
    MAKEFILE_SRC="$1"
    PARAMFILE="$2"
else
    echo "[ERROR] Usage: $0 [Makefile path] [Parameter file path]"
    echo "[ERROR] Or provide no arguments to use defaults in current directory"
    echo "[FAIL] Script aborted, but shell remains active."
    return_code=1
fi

# --- Проверка Makefile ---
if [ ! -f "$MAKEFILE_SRC" ]; then
    echo "[ERROR] Makefile not found: $MAKEFILE_SRC"
    echo "[FAIL] Script aborted."
    return_code=2
fi

# --- Проверка параметр-файла ---
if [ ! -f "$PARAMFILE" ]; then
    echo "[ERROR] Parameter file not found: $PARAMFILE"
    echo "[FAIL] Script aborted."
    return_code=3
fi

# --- Прерывание при предыдущих ошибках ---
if [ -n "$return_code" ]; then
    echo "[INFO] Script finished with error code $return_code (but shell is intact)"
    return_code=0
    exit 0
fi

# --- Копируем файлы в директорию GADGET ---
echo "[INFO] Preparing GADGET-2 build..."
cp "$MAKEFILE_SRC" "$GADGET_DIR/Makefile"
PARAM_BASENAME=$(basename "$PARAMFILE")
cp "$PARAMFILE" "$GADGET_DIR/$PARAM_BASENAME"

# --- Компиляция ---
echo "[INFO] Building Gadget2 in $GADGET_DIR..."
make -C "$GADGET_DIR" clean && make -C "$GADGET_DIR"
build_status=$?

if [ "$build_status" -ne 0 ]; then
    echo "[ERROR] Compilation failed with status $build_status"
    echo "[FAIL] Script aborted."
fi

# --- Копируем исполняемый файл обратно ---
echo "[INFO] Copying Gadget2 executable to working directory..."
cp "$GADGET_DIR/$EXECUTABLE" "$CALL_DIR/"

# --- Запуск симуляции ---
echo "[INFO] Running simulation with $PARAM_BASENAME"
cp "$PARAMFILE" "$CALL_DIR/$PARAM_BASENAME"
mpirun --allow-run-as-root -n 1 ./"$EXECUTABLE" "$PARAM_BASENAME"
run_status=$?

if [ "$run_status" -ne 0 ]; then
    echo "[ERROR] Gadget2 terminated with code $run_status"
else
    echo "[INFO] Simulation completed successfully."
fi

echo "[INFO] Script finished without shell termination."
