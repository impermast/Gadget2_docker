#!/bin/bash
# generate_ics.sh — генерация начальных условий (IC) для GIZMO через GalIC
#
# Использование:
#   bash generate_ics.sh --config config.json [--dry-run]
#

set -euo pipefail

# ======== Константы ========
NBODY_ROOT="/nbody"
GALIC_BIN="/opt/GalIC/GalIC"
GALIC_PARAM="${NBODY_ROOT}/GalIC/halo_nfw_ics.param"
MERGE_SCRIPT="${NBODY_ROOT}/scripts/merge_ics.py"
TEMPLATE_PARAM="${NBODY_ROOT}/GalIC/halo_nfw_ics.param"
LD_LIBRARY_PATH="/opt/gsl/lib:/opt/fftw/lib:/usr/lib/x86_64-linux-gnu/hdf5/openmpi:${LD_LIBRARY_PATH:-}"

info()  { echo "[INFO]  $*" >&2; }
warn()  { echo "[WARN]  $*" >&2; }
error() { echo "[ERROR] $*" >&2; }

# ======== Проверка зависимостей ========
preflight() {
    local errors=0
    if [[ ! -x "$GALIC_BIN" ]]; then
        error "GalIC binary не найден или не исполняемый: $GALIC_BIN"
        errors=1
    fi
    if [[ ! -f "$TEMPLATE_PARAM" ]]; then
        error "Шаблон param не найден: $TEMPLATE_PARAM"
        errors=1
    fi
    if [[ ! -f "$MERGE_SCRIPT" ]]; then
        error "merge_ics.py не найден: $MERGE_SCRIPT"
        errors=1
    fi
    if ! command -v python3 &>/dev/null; then
        error "python3 не найден"
        errors=1
    fi
    if [[ "$errors" -ne 0 ]]; then
        error "Обнаружены ошибки, прерывание."
        exit 1
    fi
}

# ======== Запуск GalIC для одного компонента ========
# Аргументы: component_name, output_dir, n, cc, v200
generate_component() {
    local name="$1"
    local output_dir="$2"
    local n="$3"
    local cc="$4"
    local v200="$5"

    info "--- Component: $name (n=$n, cc=$cc, v200=$v200) ---"

    local work_dir="${output_dir}/galic_${name}"
    mkdir -p "$work_dir"

    # Создаём временный .param с подстановкой N, CC, V200
    local tmp_param="${work_dir}/param_${name}.param"
    cp "$TEMPLATE_PARAM" "$tmp_param"

    # Патчим N_HALO
    sed -i "s/^N_HALO[[:space:]]*[0-9]*/N_HALO         ${n}/" "$tmp_param"

    # Патчим CC (concentration)
    sed -i "s/^CC[[:space:]]*[0-9.]*/CC             ${cc}.0/" "$tmp_param"

    # Патчим V200 (circular velocity in km/s)
    sed -i "s/^V200[[:space:]]*[0-9.]*/V200          ${v200}.0/" "$tmp_param"

    # OutputDir и OutputFile — в work_dir
    sed -i "s|^OutputDir.*|OutputDir       ${work_dir}/|" "$tmp_param"

    info "Запуск GalIC для '$name'..."
    cd "$work_dir"
    "$GALIC_BIN" "param_${name}.param" >&2 2>&1
    cd "$NBODY_ROOT"

    # Находим последний HDF5-снапшот
    local last_snap
    last_snap=$(ls -t "$work_dir"/*.hdf5 2>/dev/null | head -1)
    if [[ -z "$last_snap" ]]; then
        error "GalIC не создал HDF5 для компоненты '$name'"
        return 1
    fi

    info "Последний снапшот: $last_snap"

    # Копируем в output_dir, удаляем промежуточные
    local final_file="${output_dir}/${name}.hdf5"
    cp "$last_snap" "$final_file"
    info "Сохранён: $final_file"

    # Удаляем промежуточные снапшоты (не копируем)
    rm -f "$work_dir"/*.hdf5

    echo "$final_file"
}

# ======== MAIN ========
main() {
    local config_file=""
    local dry_run=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --config)   config_file="$2"; shift 2 ;;
            --dry-run)  dry_run=1; shift ;;
            --help|-h)
                echo "Использование: $(basename "$0") --config <config.json> [--dry-run]"
                exit 0 ;;
            *)          error "Unknown option $1"; exit 1 ;;
        esac
    done

    if [[ -z "$config_file" ]]; then
        error "--config не указан"
        exit 1
    fi

    if [[ ! -f "$config_file" ]]; then
        error "Config файл не найден: $config_file"
        exit 1
    fi

    preflight

    # Читаем JSON через python3
    local run_name output_dir
    run_name=$(python3 -c "import json; c=json.load(open('$config_file')); print(c['run_name'])")
    output_dir=$(python3 -c "import json; c=json.load(open('$config_file')); print(c['output_dir'])")
    local n_components
    n_components=$(python3 -c "import json; c=json.load(open('$config_file')); print(len(c['components']))")

    info "run_name:     $run_name"
    info "output_dir:   $output_dir"
    info "components:   $n_components"

    mkdir -p "$output_dir"

    # Копируем конфиг в output_dir для воспроизводимости
    cp "$config_file" "${output_dir}/config.json"

    if [[ "$dry_run" -eq 1 ]]; then
        info "DRY RUN — показываем команды, не выполняем"
        python3 -c "
import json
c = json.load(open('$config_file'))
for comp in c['components']:
    print(f\"  Component: {comp['name']}, n={comp['n']}, cc={comp['cc']}, v200={comp['v200']}, map_to={comp['map_to']}\")
" >&2
        info "DRY RUN завершён"
        exit 0
    fi

    # Генерируем каждую компоненту
    local input_files=()
    for i in $(seq 0 $((n_components - 1))); do
        local name n cc v200
        name=$(python3 -c "import json; c=json.load(open('$config_file')); print(c['components'][$i]['name'])")
        n=$(python3 -c "import json; c=json.load(open('$config_file')); print(c['components'][$i]['n'])")
        cc=$(python3 -c "import json; c=json.load(open('$config_file')); print(c['components'][$i]['cc'])")
        v200=$(python3 -c "import json; c=json.load(open('$config_file')); print(c['components'][$i]['v200'])")

        local hdf_file
        hdf_file=$(generate_component "$name" "$output_dir" "$n" "$cc" "$v200")
        input_files+=("$hdf_file")
    done

    # Обновляем JSON с input_file для merge_ics.py
    info "Обновление config.json с input_file..."
    python3 -c "
import json, sys
c = json.load(open('$config_file'))
for i, f in enumerate(sys.argv[1:]):
    c['components'][i]['input_file'] = f
json.dump(c, open('${output_dir}/config.json', 'w'), indent=2)
print(f'Updated {len(sys.argv)-1} components')
" "${input_files[@]}"

    # Запускаем merge
    info "Запуск merge_ics.py..."
    python3 "$MERGE_SCRIPT" "${output_dir}/config.json"

    info "=== DONE ==="
    info "IC файл: ${output_dir}/${run_name}.hdf5"
}

main "$@"