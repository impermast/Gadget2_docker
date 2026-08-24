#!/bin/bash
# Batch script for SIDM and CDM runs (1 M particles each)
# Default mode is actual execution.
# Set DRY_RUN=1 to only print commands without running them.
#
# Also supports:
#   --status         — показать таблицу статуса всех прогонов и выйти
#   --status <run>   — показать статус конкретного прогона

DRY_RUN=0

# List of SIDM cross‑section values (σ)
SIGMAS=(0.1 1 2 5)

# Paths to the GalIC JSON configuration files
SIDM_CFG="ics/sidm_N1e6.json"
CDM_CFG="ics/cdm_N1e6.json"

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERROR] $*"; }

# ----------------------------------------------------------------------
# Function: print_status_table — читает run.state из каждого прогона
# ----------------------------------------------------------------------
print_status_table() {
    local filter="$1"  # опционально: имя конкретного прогона

    # Собираем список прогонов
    local runs=()
    if [ -n "$filter" ]; then
        if [ -d "runs/$filter" ]; then
            runs=("runs/$filter")
        else
            error "Прогон не найден: runs/$filter"
            return 1
        fi
    else
        for d in runs/*/; do
            [ -d "$d" ] && runs+=("$d")
        done
        # Добавляем запланированные, но ещё не созданные прогоны
        for sigma in "${SIGMAS[@]}"; do
            local rd="runs/sidm_sigma${sigma}_N1e6"
            local found=0
            for d in "${runs[@]}"; do [ "$d" = "$rd/" ] && found=1; done
            [ "$found" -eq 0 ] && runs+=("$rd")
        done
        local rd="runs/cdm_N1e6"
        local found=0
        for d in "${runs[@]}"; do [ "$d" = "$rd/" ] && found=1; done
        [ "$found" -eq 0 ] && runs+=("$rd")
    fi

    # Заголовок таблицы
    printf "%-30s %-12s %-8s %-5s %-7s %-8s %-8s\n" \
        "RUN" "STATUS" "TIME" "SNP" "PROGRESS" "MEM(MB)" "ELAPSED"
    printf "%-30s %-12s %-8s %-5s %-7s %-8s %-8s\n" \
        "------------------------------" "------------" "--------" "-----" "-------" "--------" "--------"

    for d in "${runs[@]}"; do
        local dir="${d%/}"  # убираем завершающий слеш
        local state_file="${dir}/run.state"
        local run_name
        run_name=$(basename "$dir")

        if [ -f "$state_file" ]; then
            # Читаем state-файл
            local status="" time_val="" snaps="" progress="" mem="" elapsed="" sigma=""
            status=$(grep '^STATUS=' "$state_file" 2>/dev/null | cut -d= -f2) || status="N/A"
            time_val=$(grep '^TIME=' "$state_file" 2>/dev/null | cut -d= -f2) || time_val="—"
            snaps=$(grep '^SNAPSHOTS=' "$state_file" 2>/dev/null | cut -d= -f2) || snaps="—"
            progress=$(grep '^PROGRESS=' "$state_file" 2>/dev/null | cut -d= -f2) || progress="—"
            mem=$(grep '^MEM_MB=' "$state_file" 2>/dev/null | cut -d= -f2) || mem="—"
            elapsed=$(grep '^ELAPSED_MIN=' "$state_file" 2>/dev/null | cut -d= -f2) || elapsed="—"

            if [ "$status" = "COMPLETED" ]; then
                printf "\033[32m%-30s %-12s %-8s %-5s %-7s %-8s %-8s\033[0m\n" \
                    "$run_name" "$status" "$time_val" "$snaps" "${progress}%" "$mem" "${elapsed}min"
            elif [ "$status" = "RUNNING" ]; then
                printf "\033[33m%-30s %-12s %-8s %-5s %-7s %-8s %-8s\033[0m\n" \
                    "$run_name" "$status" "$time_val" "$snaps" "${progress}%" "$mem" "${elapsed}min"
            elif [ "$status" = "FAILED" ]; then
                printf "\033[31m%-30s %-12s %-8s %-5s %-7s %-8s %-8s\033[0m\n" \
                    "$run_name" "$status" "$time_val" "$snaps" "${progress}%" "$mem" "${elapsed}min"
            else
                printf "%-30s %-12s %-8s %-5s %-7s %-8s %-8s\n" \
                    "$run_name" "$status" "$time_val" "$snaps" "${progress}%" "$mem" "${elapsed}min"
            fi
        else
            # Проверяем, существует ли директория с output
            if [ -d "${dir}/output" ]; then
                local sn
                sn=$(ls "${dir}/output"/snapshot_*.hdf5 2>/dev/null | wc -l)
                printf "\033[33m%-30s %-12s %-8s %-5s %-7s %-8s %-8s\033[0m\n" \
                    "$run_name" "NO STATE" "?" "$sn" "?" "?" "?"
            else
                # Прогон ещё не начинался
                printf "%-30s %-12s %-8s %-5s %-7s %-8s %-8s\n" \
                    "$run_name" "NOT START" "—" "—" "—" "—" "—"
            fi
        fi
    done
}

# ----------------------------------------------------------------------
# Function: generate ICs using generate_ics.sh
# ----------------------------------------------------------------------
generate_ics() {
    local cfg=$1
    echo "Generating ICs for ${cfg} ..."
    if [ $DRY_RUN -eq 0 ]; then
        scripts/generate_ics.sh --config "${cfg}"
    else
        echo "[DRY]  scripts/generate_ics.sh --config ${cfg}"
    fi
}

# ----------------------------------------------------------------------
# Parse --status flag (must come before DRY_RUN)
# ----------------------------------------------------------------------
if [ $# -gt 0 ] && [ "$1" = "--status" ]; then
    print_status_table "$2"
    exit 0
fi

DRY_RUN=0

# Paths to the generated HDF5 files (without the .hdf5 suffix)
SIDM_IC="/nbody/ics/sidm_N1e6/sidm_N1e6"
CDM_IC="/nbody/ics/cdm_N1e6/cdm_N1e6"

# ----------------------------------------------------------------------
# Generate ICs for SIDM and CDM (if not already present)
# ----------------------------------------------------------------------
if [ ! -f "${SIDM_IC}.hdf5" ]; then
    generate_ics "$SIDM_CFG"
else
    info "SIDM IC already exists: ${SIDM_IC}.hdf5 — skipping"
fi

if [ ! -f "${CDM_IC}.hdf5" ]; then
    generate_ics "$CDM_CFG"
else
    info "CDM IC already exists: ${CDM_IC}.hdf5 — skipping"
fi

# ----------------------------------------------------------------------
# Function: run a single GIZMO simulation via run_sim.sh
# ----------------------------------------------------------------------
run_simulation() {
    local run_name=$1   # e.g. sidm_sigma0.1_N1e6
    local sim_type=$2   # cdm or sidm
    local sigma=$3      # optional, only for SIDM
    local ic_path=$4    # path to IC file without .hdf5

    local cmd=(bash scripts/run_sim.sh --name "${run_name}" --type "${sim_type}" --ic-file "${ic_path}" --mpi-procs 8)
    if [ -n "$sigma" ]; then
        cmd+=(--sigma "${sigma}")
    fi

    if [ $DRY_RUN -eq 1 ]; then
        echo "[DRY]  ${cmd[*]}"
    else
        "${cmd[@]}"
    fi
}

# ----------------------------------------------------------------------
# SIDM runs for each sigma value
# ----------------------------------------------------------------------
for sigma in "${SIGMAS[@]}"; do
    RUN_NAME="sidm_sigma${sigma}_N1e6"
    run_simulation "$RUN_NAME" "sidm" "$sigma" "$SIDM_IC"
    info "=== Статус после ${RUN_NAME} ==="
    print_status_table
    echo ""
done

# ----------------------------------------------------------------------
# CDM control run
# ----------------------------------------------------------------------
run_simulation "cdm_N1e6" "cdm" "" "$CDM_IC"
info "=== Статус после cdm_N1e6 ==="
print_status_table
echo ""

# ----------------------------------------------------------------------
# Post‑processing: multi-run comparison via plot_scripts (dry-run prints command)
# ----------------------------------------------------------------------
if [ $DRY_RUN -eq 0 ]; then
    RUN_ARGS=""
    for sigma in "${SIGMAS[@]}"; do
        RUN_ARGS="$RUN_ARGS runs/sidm_sigma${sigma}_N1e6"
    done
    python3 scripts/plot_scripts/compare_runs.py runs/cdm_N1e6 $RUN_ARGS \
        --labels CDM ${SIGMAS[@]/#/SIDM} --rcore 50 \
        --outdir analyse/cdm_sidm_all
else
    echo "[DRY]  python3 scripts/plot_scripts/compare_runs.py runs/cdm_N1e6 <sidm runs> --rcore 50 --outdir analyse/cdm_sidm_all"
fi