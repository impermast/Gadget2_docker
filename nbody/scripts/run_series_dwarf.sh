#!/usr/bin/env bash
# run_series_dwarf.sh — серия прогонов dwarf_N1e6 (CDM, SIDM 0.1/1/5) на 10 ядрах
# с промежуточными TG-уведомлениями между прогонами (ETA по факту) и
# финальным анализом: run_full_test по каждому run + compare_runs (5 серий
# включая готовый sidm20_dwarf_N1e6_T5) + TG-репорт с графиками.
#
# Запуск (внутри контейнера):
#   nohup bash /nbody/scripts/run_series_dwarf.sh > /nbody/runs/series_dwarf.log 2>&1 &
set -uo pipefail

# 10 MPI-процессов на 16 hwthreads (8 физ. ядер × 2 HT):
# OpenMPI по умолчанию считает только физические ядра (8 слотов),
# env-переменная разрешает hwthreads как слоты.
export OMPI_MCA_hwloc_base_use_hwthreads_as_cpus=1
PROCS=10
IC=/nbody/ics/dwarf_N1e6/dwarf_N1e6
TIME_MAX=5.0
TIME_BET=0.1
RCORE=2
OUTDIR=/nbody/analyse/dwarf_series
LOG=/nbody/runs/series_dwarf.log
MSGFILE=/tmp/series_tg_msg.txt

RUN_NAMES=(cdm_dwarf_N1e6_T5 sidm0.1_dwarf_N1e6_T5 sidm1_dwarf_N1e6_T5 sidm5_dwarf_N1e6_T5)
RUN_TYPES=(cdm sidm sidm sidm)
RUN_SIGMAS=("" 0.1 1 5)
# оценки на 10 ядрах, часы (калибруются по факту после каждого прогона)
EST_H=(4.5 5.0 6.0 7.0)

tg_send() {
  python3 -c "import sys;sys.path.insert(0,'/nbody/tg');from tg_notify import TgNotify;TgNotify().send_message(open('$1').read())" >/dev/null 2>&1 || true
}

tg_photo() { # $1 caption, $2 path
  python3 -c "import sys;sys.path.insert(0,'/nbody/tg');from tg_notify import TgNotify;TgNotify().send_photo('$1','$2')" >/dev/null 2>&1 || true
}

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

fmt_min() { # минуты -> "Xh Ym"
  local m=$1
  echo "$((m / 60))h $((m % 60))m"
}

sum_est_min_from() { # $1 = стартовый индекс; с учётом коэффициента $2
  local start=$1 ratio=$2 total=0 i
  for ((i = start; i < ${#RUN_NAMES[@]}; i++)); do
    total=$(python3 -c "print(int($total + ${EST_H[$i]} * 60 * $ratio))")
  done
  echo "$total"
}

snap_count() { ls /nbody/runs/$1/output/snapshot_*.hdf5 2>/dev/null | wc -l; }

log "=== SERIES START: ${RUN_NAMES[*]} (procs=$PROCS) ==="

cat > "$MSGFILE" <<EOF
🚀 СЕРИЯ DWARF_N1E6 ЗАПУЩЕНА (10 ядер)

Прогоны (последовательно):
  1. cdm_dwarf_N1e6_T5
  2. sidm0.1_dwarf_N1e6_T5
  3. sidm1_dwarf_N1e6_T5
  4. sidm5_dwarf_N1e6_T5

IC: dwarf_N1e6 (V200=30, cc=15), TimeMax=5, TimeBet=0.1
Оценка суммарно: ~$(fmt_min "$(sum_est_min_from 0 1.0)")
По завершении каждого прогона — промежуточное уведомление с ETA.
EOF
tg_send "$MSGFILE"

ratio=1.0
declare -a STATUS WALL_MIN
for i in "${!RUN_NAMES[@]}"; do
  name=${RUN_NAMES[$i]}
  type=${RUN_TYPES[$i]}
  sigma=${RUN_SIGMAS[$i]}
  est_min=$(python3 -c "print(int(${EST_H[$i]} * 60 * $ratio))")

  log "=== RUN START: $name (type=$type sigma=$sigma, est=$(fmt_min "$est_min")) ==="
  start_s=$(date +%s)

  if [[ "$type" == "cdm" ]]; then
    bash /nbody/scripts/run_sim.sh --name "$name" --type cdm \
      --time-max "$TIME_MAX" --time-bet "$TIME_BET" \
      --ic-file "$IC" --mpi-procs "$PROCS" >> "$LOG" 2>&1
  else
    bash /nbody/scripts/run_sim.sh --name "$name" --type sidm --sigma "$sigma" \
      --time-max "$TIME_MAX" --time-bet "$TIME_BET" \
      --ic-file "$IC" --mpi-procs "$PROCS" >> "$LOG" 2>&1
  fi
  rc=$?
  wall_min=$(( ($(date +%s) - start_s) / 60 ))
  STATUS[$i]=$rc
  WALL_MIN[$i]=$wall_min

  if [[ $rc -ne 0 ]]; then
    log "=== RUN FAILED: $name (rc=$rc, $(fmt_min "$wall_min")) ==="
    cat > "$MSGFILE" <<EOF
❌ $name — ОШИБКА (exit $rc) после $(fmt_min "$wall_min")

Лог: /nbody/runs/$name/run.log
Серия продолжается следующими прогонами.
EOF
    tg_send "$MSGFILE"
    continue
  fi

  # калибровка ETA по факту
  if [[ $est_min -gt 0 ]]; then
    ratio=$(python3 -c "print(round(0.5 * $ratio + 0.5 * ($wall_min / $est_min), 3))")
  fi

  n_left=$(( ${#RUN_NAMES[@]} - i - 1 ))
  eta_left=$(sum_est_min_from $((i + 1)) "$ratio")
  next_name=""
  [[ $n_left -gt 0 ]] && next_name=${RUN_NAMES[$((i + 1))]}

  cat > "$MSGFILE" <<EOF
✅ $name завершён за $(fmt_min "$wall_min")
Снапшотов: $(snap_count "$name") (ожидалось 52)

Осталось прогонов: $n_left (~$(fmt_min "$eta_left"))
EOF
  if [[ -n "$next_name" ]]; then
    echo "Следующий: $next_name (~$(fmt_min "$(python3 -c "print(int(${EST_H[$((i + 1))]} * 60 * $ratio))")"))" >> "$MSGFILE"
  else
    echo "Далее: анализ всех прогонов + сравнение с sidm20 + финальный репорт" >> "$MSGFILE"
  fi
  tg_send "$MSGFILE"
  log "=== RUN DONE: $name ($(fmt_min "$wall_min")), ratio=$ratio ==="
done

# ───────────────────────────── АНАЛИЗ ─────────────────────────────────────
cat > "$MSGFILE" <<EOF
🔬 Симуляции завершены. Начинаю анализ:
  - run_full_test по каждому прогону (профили + GIF + сводка)
  - compare_runs: CDM / SIDM 0.1 / 1 / 5 / 20 на одних IC
Ориентир: ~10-15 минут.
EOF
tg_send "$MSGFILE"
log "=== ANALYSIS PHASE START ==="

analyze_fail=0
for name in "${RUN_NAMES[@]}"; do
  log "--- analysis: $name ---"
  if ! python3 /nbody/scripts/plot_scripts/run_full_test.py \
        --run-root "/nbody/runs/$name" >> "$LOG" 2>&1; then
    analyze_fail=$((analyze_fail + 1))
    log "ANALYSIS FAILED: $name"
  fi
done

log "--- compare_runs (5 серий, rcore=$RCORE) ---"
# ВАЖНО: позиционные аргументы (run-каталоги) — ДО --labels, т.к. nargs='*'
if ! python3 /nbody/scripts/plot_scripts/compare_runs.py \
      --outdir "$OUTDIR" --rcore "$RCORE" \
      /nbody/runs/cdm_dwarf_N1e6_T5 \
      /nbody/runs/sidm0.1_dwarf_N1e6_T5 \
      /nbody/runs/sidm1_dwarf_N1e6_T5 \
      /nbody/runs/sidm5_dwarf_N1e6_T5 \
      /nbody/runs/sidm20_dwarf_N1e6_T5 \
      --labels CDM SIDM0.1 SIDM1 SIDM5 SIDM20 >> "$LOG" 2>&1; then
  analyze_fail=$((analyze_fail + 1))
  log "COMPARE FAILED"
fi

# ───────────────────────── ФИНАЛЬНЫЙ РЕПОРТ ───────────────────────────────
{
  echo "🏁 СЕРИЯ DWARF_N1E6 ЗАВЕРШЕНА"
  echo ""
  echo "Прогоны:"
  for i in "${!RUN_NAMES[@]}"; do
    name=${RUN_NAMES[$i]}
    if [[ ${STATUS[$i]:-1} -eq 0 ]]; then
      st="✅ $(fmt_min "${WALL_MIN[$i]:-0}"), снапшотов: $(snap_count "$name")"
    else
      st="❌ exit ${STATUS[$i]:-?}"
    fi
    echo "  $((i + 1)). $name — $st"
  done
  echo ""
  echo "Метрики (r<${RCORE} kpc / inner slope):"
  for name in "${RUN_NAMES[@]}"; do
    f="/nbody/runs/$name/plots/summary_analysis.txt"
    if [[ -f "$f" ]]; then
      rc_line=$(grep 'Core density' "$f" | head -1)
      sl_line=$(grep 'Inner log-slope' "$f" | head -1)
      echo "  $name: ${rc_line#*Core density } | ${sl_line#*Inner log-slope (median first bins): }"
    fi
  done
  echo ""
  echo "Анализ: $([[ $analyze_fail -eq 0 ]] && echo 'успешно' || echo "ошибок: $analyze_fail")"
  echo "Графики сравнения: $OUTDIR/"
  echo "Лог серии: $LOG"
} > "$MSGFILE"
tg_send "$MSGFILE"

for png in density_compare log_slope_compare sigma_v_compare core_density_vs_sigma; do
  [[ -f "$OUTDIR/$png.png" ]] && tg_photo "dwarf_series: $png" "$OUTDIR/$png.png"
done

log "=== SERIES COMPLETE (analyze_fail=$analyze_fail) ==="

