#!/bin/bash
# run_sim.sh — универсальный запускатор GIZMO (CDM/SIDM)
#
# Использование:
#   bash run_sim.sh --name myrun --type sidm --time-max 5.0 --sigma 10
#   bash run_sim.sh --name myrun --type cdm  --time-max 0.1 --dry-run
#   bash run_sim.sh --name myrun --type sidm --tg
#
# Обязательные:
#   --name <name>     имя прогона (создаётся nbody/runs/<name>/)
#   --type <cdm|sidm> тип симуляции
#
# Опциональные:
#   --time-max <t>       TimeMax (по умолчанию из шаблона)
#   --time-bet <t>       TimeBetSnapshot (по умолчанию из шаблона)
#   --sigma <s>          DM_InteractionCrossSection (только для sidm, по умолчанию 10)
#   --ic-file <path>     InitCondFile (по умолч. /nbody/gizmo_test/halo_10000_sidm_ic)
#   --mpi-procs <n>      число MPI процессов (по умолчанию 4)
#   --rebuild            принудительная пересборка GIZMO
#   --dry-run            только показать что будет сделано
#   --skip-viz           пропустить check_snapshot.py после прогона
#   --tg                 включить Telegram-уведомления
#   --tg-interval <n>    интервал прогресса в минутах (по умолчанию 10, только с --tg)
#   --tg-skip-progress   не отправлять прогресс-уведомления (только старт/финиш)

set -euo pipefail

# ======== Конфигурация по умолчанию ========
GIZMO_SRC="/opt/gizmo-public"
GIZMO_BIN="${GIZMO_SRC}/GIZMO"
TEMPLATE_DIR="/nbody/gizmo_test"
BASE_DIR="/nbody/runs"
# experimentLog.md лежит на хосте вне точки монтирования /nbody.
# Внутри контейнера записываем лог в директорию прогона.
# На хосте можно вручную объединить: cat ${RUN_DIR}/experiment.md >> llm/memory-bank/experimentLog.md
EXPERIMENT_LOG=""

# ======== Парсинг аргументов ========
RUN_NAME=""
SIM_TYPE=""
TIME_MAX=""
TIME_BET=""
SIGMA=""
IC_FILE=""
MPI_PROCS=4
REBUILD=0
DRY_RUN=0
SKIP_VIZ=0
TG_FLAG=0
TG_INTERVAL=10
TG_SKIP_PROGRESS=0
TG_SCRIPT="/nbody/tg/tg_event.py"

usage() {
    cat << 'EOF'
Использование: run_sim.sh --name <name> --type <cdm|sidm> [опции]

Обязательные:
  --name <name>       имя директории прогона (nbody/runs/<name>/)
  --type <cdm|sidm>   CDM или SIDM симуляция

Опциональные:
  --time-max <t>      TimeMax (по умолчанию из шаблона)
  --time-bet <t>      TimeBetSnapshot (по умолчанию из шаблона)
  --sigma <s>         сечение SIDM (только для --type sidm, по умолч. 10)
  --ic-file <path>    путь к IC-файлу (без .hdf5)
  --mpi-procs <n>     число MPI процессов (по умолчанию 4)
  --rebuild           принудительная пересборка GIZMO
  --dry-run           только показать команды без запуска
  --skip-viz          не запускать check_snapshot.py после прогона
  --tg                включить Telegram-уведомления
  --tg-interval <n>   интервал прогресса в минутах (по умолч. 10, только с --tg)
  --tg-skip-progress  не отправлять прогресс-уведомления (только старт/финиш)
EOF
}

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERROR] $*"; }

# ======== Валидация ========
validate() {
    local errors=0

    if [[ -z "$RUN_NAME" ]]; then
        error "--name не указан"; errors=1
    fi
    if [[ "$SIM_TYPE" != "cdm" && "$SIM_TYPE" != "sidm" ]]; then
        error "--type должен быть cdm или sidm"; errors=1
    fi
    if [[ ! -d "$GIZMO_SRC" ]]; then
        error "GIZMO исходники не найдены: $GIZMO_SRC"; errors=1
    fi
    if [[ ! -f "${TEMPLATE_DIR}/Config_cdm_sidm.sh" ]]; then
        error "Config.sh не найден: ${TEMPLATE_DIR}/Config_cdm_sidm.sh"; errors=1
    fi

    local param_src=""
    if [[ "$SIM_TYPE" == "cdm" ]]; then
        param_src="${TEMPLATE_DIR}/gizmo_cdm.param"
    else
        param_src="${TEMPLATE_DIR}/gizmo_sidm.param"
    fi
    if [[ ! -f "$param_src" ]]; then
        error "Param файл не найден: $param_src"; errors=1
    fi

    # IC file
    local ic_resolved="${IC_FILE}"
    if [[ -z "$ic_resolved" ]]; then
        ic_resolved="/nbody/gizmo_test/halo_10000_sidm_ic"
    fi
    ic_resolved="${ic_resolved%.hdf5}"
    if [[ ! -f "${ic_resolved}.hdf5" ]]; then
        error "IC файл не найден: ${ic_resolved}.hdf5"; errors=1
    fi
    IC_FILE="${ic_resolved}"

    # Директория прогона — не должна существовать
    RUN_DIR="${BASE_DIR}/${RUN_NAME}"
    if [[ -d "$RUN_DIR" ]]; then
        error "Директория уже существует: ${RUN_DIR}"
        warn "Удалите или выберите другое --name"
        errors=1
    fi

    if ! command -v mpirun &>/dev/null; then
        error "mpirun не найден"; errors=1
    fi
    if ! command -v python3 &>/dev/null; then
        error "python3 не найден"; errors=1
    fi
    if [[ "$SKIP_VIZ" -eq 0 ]] && [[ ! -f "/nbody/scripts/check_snapshot.py" ]]; then
        warn "check_snapshot.py не найден, пост-обработка отключена"
        SKIP_VIZ=1
    fi

    # Telegram-скрипт
    if [[ "$TG_FLAG" -eq 1 ]]; then
        if [[ ! -f "$TG_SCRIPT" ]]; then
            warn "--tg включён, но $TG_SCRIPT не найден. Отключаю TG."
            TG_FLAG=0
        else
            info "Telegram-уведомления включены"
        fi
    fi

    if [[ "$errors" -ne 0 ]]; then
        error "Обнаружены ошибки, прерывание."
        exit 1
    fi
}

# ======== Preflight (dry-run) ========
preflight() {
    info "=== PREFLIGHT ==="
    info "Имя прогона:      $RUN_NAME"
    info "Тип:              $SIM_TYPE"
    info "IC файл:          ${IC_FILE}.hdf5"
    info "MPI процессов:    $MPI_PROCS"
    info "Директория:       $RUN_DIR"
    if [[ "$SIM_TYPE" == "cdm" ]]; then
        info "Параметры:        ${TEMPLATE_DIR}/gizmo_cdm.param"
    else
        info "Параметры:        ${TEMPLATE_DIR}/gizmo_sidm.param"
    fi
    [[ -n "$TIME_MAX" ]] && info "TimeMax:          $TIME_MAX"
    [[ -n "$TIME_BET" ]] && info "TimeBetSnapshot:  $TIME_BET"
    [[ -n "$SIGMA" ]]    && info "SIDM sigma:       $SIGMA"
    [[ "$REBUILD" -eq 1 ]] && info "Пересборка:       да"
    [[ "$TG_FLAG" -eq 1 ]] && info "Telegram:         вкл (прогресс: раз в ${TG_INTERVAL} мин)"
    [[ "$TG_FLAG" -eq 1 && "$TG_SKIP_PROGRESS" -eq 1 ]] && info "Telegram:         прогресс отключён"
    if [[ -f "$GIZMO_BIN" ]]; then
        info "Бинарник:         $GIZMO_BIN (существует)"
    else
        info "Бинарник:         не найден, будет собран"
    fi
    info "Команда: mpirun --allow-run-as-root -np $MPI_PROCS ${GIZMO_BIN} ${RUN_DIR}/.gizmo_run.param"
    info "=== PREFLIGHT DONE ==="
}

# ======== Подготовка директории ========
setup_run_dir() {
    info "Создание директории ${RUN_DIR}"
    mkdir -p "${RUN_DIR}/configs"
    mkdir -p "${RUN_DIR}/output"
    mkdir -p "${RUN_DIR}/plots"

    cp "${TEMPLATE_DIR}/Config_cdm_sidm.sh" "${RUN_DIR}/configs/Config.sh"

    if [[ "$SIM_TYPE" == "cdm" ]]; then
        PARAM_SRC="${TEMPLATE_DIR}/gizmo_cdm.param"
    else
        PARAM_SRC="${TEMPLATE_DIR}/gizmo_sidm.param"
    fi
    cp "$PARAM_SRC" "${RUN_DIR}/.gizmo_run.param"
    cp "$PARAM_SRC" "${RUN_DIR}/configs/"

    # Патчинг
    local abs_out="${RUN_DIR}/output"
    sed -i "s|^InitCondFile.*|InitCondFile  ${IC_FILE}|"   "${RUN_DIR}/.gizmo_run.param"
    sed -i "s|^OutputDir.*|OutputDir  ${abs_out}/|"        "${RUN_DIR}/.gizmo_run.param"

    if [[ -n "$TIME_MAX" ]]; then
        if grep -q '^TimeMax' "${RUN_DIR}/.gizmo_run.param"; then
            sed -i "s|^TimeMax[[:space:]]*.*|TimeMax     ${TIME_MAX}|" "${RUN_DIR}/.gizmo_run.param"
        else
            echo "TimeMax     ${TIME_MAX}" >> "${RUN_DIR}/.gizmo_run.param"
        fi
    fi

    if [[ -n "$TIME_BET" ]]; then
        if grep -q '^TimeBetSnapshot' "${RUN_DIR}/.gizmo_run.param"; then
            sed -i "s|^TimeBetSnapshot[[:space:]]*.*|TimeBetSnapshot     ${TIME_BET}|" "${RUN_DIR}/.gizmo_run.param"
        else
            echo "TimeBetSnapshot     ${TIME_BET}" >> "${RUN_DIR}/.gizmo_run.param"
        fi
    fi

    if [[ "$SIM_TYPE" == "sidm" && -n "$SIGMA" ]]; then
        if grep -q '^DM_InteractionCrossSection' "${RUN_DIR}/.gizmo_run.param"; then
            sed -i "s|^DM_InteractionCrossSection[[:space:]]*.*|DM_InteractionCrossSection    ${SIGMA}|" "${RUN_DIR}/.gizmo_run.param"
        else
            echo "DM_InteractionCrossSection    ${SIGMA}" >> "${RUN_DIR}/.gizmo_run.param"
        fi
    fi

    info "Рабочий .param: ${RUN_DIR}/.gizmo_run.param"
}

# ======== Сборка GIZMO ========
rebuild_gizmo() {
    if [[ "$REBUILD" -eq 0 && -f "$GIZMO_BIN" ]]; then
        local config_md5
        config_md5=$(md5sum "${RUN_DIR}/configs/Config.sh" 2>/dev/null | cut -d' ' -f1)
        local ref_md5=""
        if [[ -f "${GIZMO_SRC}/.last_build_config.md5" ]]; then
            ref_md5=$(cat "${GIZMO_SRC}/.last_build_config.md5")
        fi
        if [[ "$config_md5" == "$ref_md5" ]]; then
            info "Config.sh не изменился, пропускаем сборку"
            return 0
        fi
        info "Config.sh изменился, пересобираем GIZMO"
    fi

    cp "${RUN_DIR}/configs/Config.sh" "${GIZMO_SRC}/Config.sh"
    cd "$GIZMO_SRC"
    make clean 2>&1 | tail -2 || true
    make -j"$(nproc)" 2>&1 | tail -5
    cd /nbody

    if command -v md5sum &>/dev/null; then
        md5sum "${RUN_DIR}/configs/Config.sh" | cut -d' ' -f1 > "${GIZMO_SRC}/.last_build_config.md5"
    fi

    if [[ ! -f "$GIZMO_BIN" ]]; then
        error "Сборка не удалась"
        exit 1
    fi
    info "Сборка завершена: $GIZMO_BIN"
}

# ======== Watcher — обновление run.state раз в минуту ========
start_watcher() {
    local run_dir="$1"
    local param_file="${run_dir}/.gizmo_run.param"
    local state_file="${run_dir}/run.state"
    local start_epoch
    start_epoch=$(date +%s)

    # Читаем TimeMax из .gizmo_run.param
    local time_max
    time_max=$(grep -i '^TimeMax[[:space:]]' "$param_file" 2>/dev/null | awk '{print $2}' || echo "N/A")

    # Telegram: счётчик циклов для прогресса
    local tg_cycle=0

    (
    while true; do
        # Telegram: прогресс по расписанию
        if [[ "$TG_FLAG" -eq 1 && "$TG_SKIP_PROGRESS" -eq 0 ]]; then
            tg_cycle=$((tg_cycle + 1))
            if [[ $((tg_cycle * 60)) -ge $((TG_INTERVAL * 60)) ]] || [[ "$tg_cycle" -eq 1 ]]; then
                tg_cycle=0
                python3 "$TG_SCRIPT" --event progress --state "$state_file" 2>/dev/null || true
            fi
        fi
        # Проверяем, жив ли mpirun
        local pid=""
        local alive=0
        pid=$(pgrep -f "mpirun.*${run_dir}" 2>/dev/null | head -1)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            alive=1
        fi
        if [[ "$alive" -eq 0 ]]; then
            # возможно mpirun уже завершился — проверяем последнюю запись в .gizmo_run.param-usedvalues
            if [[ -f "${run_dir}/.gizmo_run.param-usedvalues" ]]; then
                # симуляция завершилась — выходим
                break
            fi
        fi

        # Последний Sync-Point из run.log
        local time_val=""
        local sync_point=""
        local last_line
        last_line=$(grep "Sync-Point" "${run_dir}/run.log" 2>/dev/null | tail -1)
        if [[ -n "$last_line" ]]; then
            sync_point=$(echo "$last_line" | awk -F', ' '{print $1}' | awk '{print $3}')
            time_val=$(echo "$last_line" | awk -F', ' '{print $2}' | awk '{print $2}')
        fi

        # Количество снапшотов
        local snaps=0
        snaps=$(ls "${run_dir}/output"/snapshot_*.hdf5 2>/dev/null | wc -l)

        # Прогресс
        local progress="N/A"
        if [[ "$time_max" != "N/A" && -n "$time_val" ]]; then
            progress=$(echo "scale=1; $time_val / $time_max * 100" | bc -l 2>/dev/null || echo "N/A")
        fi

        # Потребление памяти (RSS первого MPI процесса)
        local mem_mb="N/A"
        local gismo_pid
        gismo_pid=$(pgrep -f "^$GIZMO_BIN" 2>/dev/null | head -1)
        if [[ -n "$gismo_pid" ]]; then
            mem_mb=$(ps -o rss= -p "$gismo_pid" 2>/dev/null | awk '{printf "%.0f", $1/1024}' || echo "N/A")
        fi

        # Прошло минут
        local now_epoch
        now_epoch=$(date +%s)
        local elapsed_min=$(( (now_epoch - start_epoch) / 60 ))

        # Статус
        local status="RUNNING"
        if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
            status="STOPPED"
        fi

        # Пишем state-файл
        cat > "$state_file" << EOF
STATUS=${status}
RUN_NAME=${RUN_NAME}
SIM_TYPE=$(echo "$SIM_TYPE" | tr '[:lower:]' '[:upper:]')
SIGMA=${SIGMA:-N/A}
TIME=${time_val:-N/A}
TIME_MAX=${time_max}
PROGRESS=${progress}
SYNC_POINT=${sync_point:-N/A}
SNAPSHOTS=${snaps}
MEM_MB=${mem_mb}
ELAPSED_MIN=${elapsed_min}
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
EOF

        sleep 60
    done
    ) &
    WATCHER_PID=$!
    info "Watcher запущен (PID=$WATCHER_PID), state: ${run_dir}/run.state"
}

stop_watcher() {
    if [[ -n "${WATCHER_PID:-}" ]]; then
        kill "$WATCHER_PID" 2>/dev/null || true
        wait "$WATCHER_PID" 2>/dev/null || true
        info "Watcher остановлен"
    fi
}

# ======== Telegram-хуки ========
tg_send_start() {
    local ic_name
    ic_name=$(basename "${IC_FILE}" 2>/dev/null || echo "")
    python3 "$TG_SCRIPT" --event start \
        --name "$RUN_NAME" --type "$SIM_TYPE" \
        --sigma "${SIGMA:-N/A}" \
        --ic "$ic_name" \
        --time-max "${TIME_MAX:-}" \
        2>/dev/null || warn "TG: ошибка отправки START"
}

tg_send_finish() {
    local st=$1
    python3 "$TG_SCRIPT" --event finish \
        --name "$RUN_NAME" \
        --status "$st" \
        --state "${RUN_DIR}/run.state" \
        2>/dev/null || warn "TG: ошибка отправки FINISH"
}

# ======== Запуск симуляции ========
run_simulation() {
    info "Запуск симуляции..."
    info "Лог: ${RUN_DIR}/run.log"

    # Telegram: старт
    if [[ "$TG_FLAG" -eq 1 ]]; then
        tg_send_start
    fi

    # Запускаем watcher
    start_watcher "${RUN_DIR}"

    cd "${RUN_DIR}"
    mpirun --allow-run-as-root -np "$MPI_PROCS" "$GIZMO_BIN" ".gizmo_run.param" 2>&1 | tee "run.log"
    local status=$?

    # Останавливаем watcher
    stop_watcher

    # Обновляем state-файл финальным статусом
    if [[ "$status" -eq 0 ]]; then
        sed -i 's/^STATUS=.*/STATUS=COMPLETED/' "${RUN_DIR}/run.state" 2>/dev/null || true
        info "Симуляция завершена успешно"
    else
        sed -i 's/^STATUS=.*/STATUS=FAILED/' "${RUN_DIR}/run.state" 2>/dev/null || true
        warn "Симуляция завершилась с кодом $status"
    fi

    # Telegram: финиш
    if [[ "$TG_FLAG" -eq 1 ]]; then
        tg_send_finish "$status"
    fi

    return "$status"
}

# ======== Пост-обработка ========
postprocess() {
    info "Пост-обработка..."
    local last_snap
    last_snap=$(ls -t "${RUN_DIR}/output"/snapshot_*.hdf5 2>/dev/null | head -1)
    if [[ -z "$last_snap" ]]; then
        warn "Снапшоты не найдены"
        return 1
    fi
    info "Последний снапшот: $last_snap"
    python3 /nbody/scripts/check_snapshot.py "$last_snap" 3 2>&1 | tee "${RUN_DIR}/snapshot_check.txt"
    info "Результат: ${RUN_DIR}/snapshot_check.txt"
}

# ======== Логирование эксперимента ========
log_experiment() {
    local run_status=$1
    local snaps=0
    local part_type=3
    local ic_basename
    ic_basename=$(basename "${IC_FILE}")

    if [[ -d "${RUN_DIR}/output" ]]; then
        snaps=$(ls "${RUN_DIR}/output"/snapshot_*.hdf5 2>/dev/null | wc -l)
    fi

    if [[ "$SIM_TYPE" == "cdm" ]]; then
        part_type=1
    fi

    # Пишем лог в директорию прогона (внутри /nbody, доступно и в контейнере, и на хосте)
    local local_log="${RUN_DIR}/experiment.md"
    info "Лог эксперимента: ${local_log}"
    if [[ -f "$local_log" ]]; then
        warn "Файл ${local_log} уже существует — дописываем"
    fi
    EXPERIMENT_LOG="$local_log"

    cat >> "$EXPERIMENT_LOG" << EOF

### $(date +%Y-%m-%d) ${RUN_NAME}

Goal:

- Automated run via run_sim.sh

Type:

- $(echo "$SIM_TYPE" | tr '[:lower:]' '[:upper:]')

Input:

- IC file: ${IC_FILE}.hdf5
- parameter file: ${RUN_DIR}/.gizmo_run.param
- config file: ${RUN_DIR}/configs/Config.sh
- run script: run_sim.sh

Key parameters:

- particle number: $(python3 -c "
import h5py; f = h5py.File('${IC_FILE}.hdf5','r')
h = f['Header'].attrs
print(h['NumPart_ThisFile'][${part_type}])
" 2>/dev/null || echo "N/A")
- SIDM cross-section: ${SIGMA:-N/A}
- runtime: ${TIME_MAX:-default}
- output cadence: ${TIME_BET:-default}
- MPI procs: ${MPI_PROCS}
- seed: N/A

Commands:

\`\`\`bash
bash /nbody/scripts/run_sim.sh --name ${RUN_NAME} --type ${SIM_TYPE} --time-max ${TIME_MAX:-default} ${SIGMA:+--sigma ${SIGMA}} --mpi-procs ${MPI_PROCS}
\`\`\`

Outputs:

- output directory: ${RUN_DIR}/output/
- snapshots: ${snaps}
- plots: ${RUN_DIR}/plots/
- logs: ${RUN_DIR}/run.log

Status:

- $( [[ "$run_status" -eq 0 ]] && echo "completed" || echo "failed" )

Notes:

- Automatically generated by run_sim.sh.
- $( [[ "$run_status" -eq 0 ]] && echo "Simulation finished normally." || echo "Simulation exited with code $run_status." )

EOF

    info "Эксперимент записан в $EXPERIMENT_LOG"
}

# ======== MAIN ========
main() {
    # Разбор аргументов
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name)      RUN_NAME="$2";    shift 2 ;;
            --type)      SIM_TYPE="$2";    shift 2 ;;
            --time-max)  TIME_MAX="$2";    shift 2 ;;
            --time-bet)  TIME_BET="$2";    shift 2 ;;
            --sigma)     SIGMA="$2";       shift 2 ;;
            --ic-file)   IC_FILE="$2";     shift 2 ;;
            --mpi-procs) MPI_PROCS="$2";   shift 2 ;;
            --rebuild)        REBUILD=1;            shift ;;
            --dry-run)        DRY_RUN=1;            shift ;;
            --skip-viz)       SKIP_VIZ=1;           shift ;;
            --tg)             TG_FLAG=1;            shift ;;
            --tg-interval)    TG_INTERVAL="$2";     shift 2 ;;
            --tg-skip-progress) TG_SKIP_PROGRESS=1; shift ;;
            --help|-h)   usage; exit 0 ;;
            *)           echo "ERROR: Unknown option $1"; usage; exit 1 ;;
        esac
    done

    validate
    preflight

    if [[ "$DRY_RUN" -eq 1 ]]; then
        info "DRY RUN — ничего не делаем"
        exit 0
    fi

    setup_run_dir
    rebuild_gizmo
    run_simulation
    local sim_status=$?

    if [[ "$SKIP_VIZ" -eq 0 ]]; then
        postprocess || true
    fi

    log_experiment "$sim_status"

    info "=== DONE ==="
    info "Директория: $RUN_DIR"
    info "Лог:        ${RUN_DIR}/run.log"
    info "Параметры:  ${RUN_DIR}/.gizmo_run.param"
    exit "$sim_status"
}

main "$@"