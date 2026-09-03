#!/usr/bin/env bash
# run_matrix_dissipation.sh — стартовая smoke-calibrated сетка CDM/SIDM/dSIDM
# (N=1e5, T=2) в группе runs/test_dissipation/.
#
# Основано на smoke-тестах 2026-08-28:
# - dsidm10_f05_k15_N1e5_T2: патологичный runaway/timestep-collapse до T=2;
# - dsidm5_f005_k0_N1e5_T2_np4: стабильный completed/ok, но диска мало
#   (NI=5194, 4.21% частиц).
#
# Поэтому anti-sticking kick=15 и f=0.5 исключены из начальной сетки, а dSIDM
# точки идут по k=0 и умеренной диссипации: f=0.05, 0.1, 0.2
# для σ=1 и σ=10 плюс подтверждённая мягкая σ=5,f=0.05.
# Финал: run_full_test по всем + TG-сводка метрик + edge-on карты.
set -uo pipefail

export OMPI_MCA_hwloc_base_use_hwthreads_as_cpus=1
# На текущем контейнере nproc=16; smoke launch с -np 10 раньше падал по slots,
# но пользователь запросил рабочую сетку на 8 процессах.
PROCS=${PROCS:-8}
IC=/nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5_k05.hdf5
TIME_MAX=2.0
TIME_BET=0.1
GROUP=${GROUP:-test_dissipation}
LOG=/nbody/runs/$GROUP/series.log
MSGFILE=/tmp/matrix_tg_msg.txt

# Стартовая сетка после smoke-тестов:
# - CDM: контроль без self-interaction;
# - SIDM σ=1, σ=5 и σ=10: упругие контроли;
# - dSIDM σ=5,f=0.05: уже подтверждённая стабильная нижняя точка;
# - dSIDM σ=1 и σ=10,f=0.05/0.1/0.2: поиск границы эффекта без kick runaway.
NAMES=(
  cdm_N1e5_T2
  sidm1_N1e5_T2
  sidm5_N1e5_T2
  sidm10_N1e5_T2
  dsidm1_f005_k0_N1e5_T2
  dsidm1_f01_k0_N1e5_T2
  dsidm1_f02_k0_N1e5_T2
  dsidm5_f005_k0_N1e5_T2
  dsidm10_f005_k0_N1e5_T2
  dsidm10_f01_k0_N1e5_T2
  dsidm10_f02_k0_N1e5_T2
)
TYPES=(cdm sidm sidm sidm sidm sidm sidm sidm sidm sidm sidm)
SIGMAS=("" 1 5 10 1 1 1 5 10 10 10)
DISSS=("" "" "" "" 0.05 0.1 0.2 0.05 0.05 0.1 0.2)
KICKS=("" "" "" "" 0 0 0 0 0 0 0)

tg_send() {
  python3 -c "import sys;sys.path.insert(0,'/nbody/tg');from tg_notify import TgNotify;TgNotify().send_message(open('$1').read(), parse_mode=None)" >/dev/null 2>&1 || true
}
tg_photo() {
  python3 -c "import sys;sys.path.insert(0,'/nbody/tg');from tg_notify import TgNotify;TgNotify().send_photo('$1','$2', parse_mode=None)" >/dev/null 2>&1 || true
}
log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
fmt_min() { local m=$1; echo "$((m / 60))h $((m % 60))m"; }
snap_count() { ls /nbody/runs/$GROUP/$1/output/snapshot_*.hdf5 2>/dev/null | wc -l; }

# Оценки времени на 8 процессах (минуты) — калибруются по факту после каждого run
EST_MIN=(18 20 22 25 25 30 35 25 35 45 60)

sum_est_min_from() { # $1 = стартовый индекс; $2 = коэффициент ratio
  local start=$1 ratio=$2 total=0 i
  for ((i = start; i < ${#NAMES[@]}; i++)); do
    total=$((total + ${EST_MIN[$i]} * 60))
  done
  python3 -c "print(int($total * $ratio / 60))"
}

# Проверка, завершён ли run (completed/ok + ожидемое число снапшотов)
is_run_complete() {
  local name=$1 state=/nbody/runs/$GROUP/$name/run.state
  [[ -f "$state" ]] || return 1
  local status; status=$(grep -oP 'STATUS=\K[A-Z]+' "$state" 2>/dev/null)
  [[ "$status" == "COMPLETED" ]] || return 1
  local snaps; snaps=$(snap_count "$name")
  [[ "$snaps" -ge 21 ]]
}

mkdir -p "/nbody/runs/$GROUP"
log "=== MATRIX START: ${#NAMES[@]} runs (procs=$PROCS) ==="

cat > "$MSGFILE" <<EOF
🧪 TEST DISSIPATION GRID (N=1e5, T=2 Gyr) — ${#NAMES[@]} прогонов
Группа: runs/$GROUP/
Состав: CDM + SIDM(σ=1,5,10) + dSIDM(kick=0; σ=1,10 по f=0.05,0.1,0.2; σ=5,f=0.05)
Процессов: $PROCS
Оценка суммарно: ~$(fmt_min "$(sum_est_min_from 0 1.0)")
По завершении каждого прогона — промежуточное уведомление с ETA.
EOF
tg_send "$MSGFILE"

declare -a STATUS WALL_MIN
FAILED=0
ratio=1.0
SERIES_START_S=$(date +%s)
COMPLETED_COUNT=0

for i in "${!NAMES[@]}"; do
  name=${NAMES[$i]}; type=${TYPES[$i]}; sigma=${SIGMAS[$i]}; diss=${DISSS[$i]}; kick=${KICKS[$i]}

  # Resume: пропускаем уже завершённые runs
  if is_run_complete "$name"; then
    STATUS[$i]=0
    WALL_MIN[$i]=0
    COMPLETED_COUNT=$((COMPLETED_COUNT+1))
    log "=== RUN SKIP (already completed): $name ==="
    continue
  fi

  log "=== RUN START: $name (type=$type sigma=${sigma:-0} diss=${diss:--} kick=${kick:--}) ==="
  start_s=$(date +%s)

  cmd=(bash /nbody/scripts/run_sim.sh
       --name "$GROUP/$name" --type "$type"
       --time-max "$TIME_MAX" --time-bet "$TIME_BET"
       --ic-file "$IC" --mpi-procs "$PROCS"
       --no-tg)
  [[ -n "$sigma" ]] && cmd+=(--sigma "$sigma")
  [[ -n "$diss" ]]  && cmd+=(--dissipation "$diss")
  [[ -n "$kick" ]]  && cmd+=(--kick "$kick")
  "${cmd[@]}" >> "$LOG" 2>&1
  rc=$?
  wall_min=$(( ($(date +%s) - start_s) / 60 ))
  STATUS[$i]=$rc; WALL_MIN[$i]=$wall_min

  if [[ $rc -ne 0 ]]; then
    FAILED=$((FAILED+1))
    log "=== RUN FAILED: $name (rc=$rc) ==="
    cat > "$MSGFILE" <<EOF
❌ $name упал за $(fmt_min "$wall_min")
Exit code: $rc
Снапшотов: $(snap_count "$name") / 21

Серия: $GROUP
Обработано: $((i+1)) / ${#NAMES[@]}
Осталось прогонов: $((${#NAMES[@]} - i - 1)) (~$(fmt_min "$(sum_est_min_from $((i + 1)) "$ratio")"))

Лог: /nbody/runs/$GROUP/$name/run.log
EOF
    tg_send "$MSGFILE"
    continue
  fi

  COMPLETED_COUNT=$((COMPLETED_COUNT+1))

  # Калибровка ETA по факту
  if [[ ${EST_MIN[$i]} -gt 0 ]]; then
    ratio=$(python3 -c "print(round(0.5 * $ratio + 0.5 * ($wall_min / ${EST_MIN[$i]}), 3))")
  fi

  n_left=$(( ${#NAMES[@]} - COMPLETED_COUNT ))
  eta_left=$(sum_est_min_from $((i + 1)) "$ratio")
  series_elapsed_min=$(( ($(date +%s) - SERIES_START_S) / 60 ))
  next_name=""
  [[ $n_left -gt 0 ]] && next_name=${NAMES[$((i + 1))]}

  cat > "$MSGFILE" <<EOF
✅ $name завершён за $(fmt_min "$wall_min")
Снапшотов: $(snap_count "$name") / 21

Серия: $GROUP
Прогресс: $COMPLETED_COUNT / ${#NAMES[@]} завершено
Суммарно идёт: $(fmt_min "$series_elapsed_min")

Осталось прогонов: $n_left (~$(fmt_min "$eta_left"))
EOF
  if [[ -n "$next_name" ]]; then
    echo "Следующий: $next_name (~$(fmt_min "$(python3 -c "print(int(${EST_MIN[$((i + 1))]} * $ratio))")"))" >> "$MSGFILE"
  else
    echo "Далее: анализ всех прогонов + финальный отчёт" >> "$MSGFILE"
  fi
  tg_send "$MSGFILE"
  log "=== RUN DONE: $name ($(fmt_min "$wall_min")), ratio=$ratio ==="
done

# ───────────────────────────── АНАЛИЗ ─────────────────────────────────────
cat > "$MSGFILE" <<EOF
🔬 Тестовая сетка завершена. Запускаю анализ (run_full_test × ${#NAMES[@]})...
EOF
tg_send "$MSGFILE"
log "=== ANALYSIS PHASE START ==="

for i in "${!NAMES[@]}"; do
  name=${NAMES[$i]}
  log "--- analysis: $name ---"
  if [[ ${STATUS[$i]:-1} -eq 0 ]]; then
    python3 /nbody/scripts/plot_scripts/run_full_test.py \
        --run-root "/nbody/runs/$GROUP/$name" >> "$LOG" 2>&1 \
      || log "ANALYSIS FAILED: $name"
  else
    log "ANALYSIS SKIPPED: $name (run failed)"
  fi
done

# ───────────────────────── ФИНАЛЬНЫЙ РЕПОРТ ───────────────────────────────
series_total_min=$(( ($(date +%s) - SERIES_START_S) / 60 ))

# Вердикт серии
ANALYSIS_FAIL=0
for i in "${!NAMES[@]}"; do
  [[ ${STATUS[$i]:-1} -eq 0 ]] || continue
  [[ -f "/nbody/runs/$GROUP/${NAMES[$i]}/plots/summary_analysis.txt" ]] || ANALYSIS_FAIL=$((ANALYSIS_FAIL+1))
done

if [[ $FAILED -gt 0 ]]; then
  VERDICT="ОШИБКА"
elif [[ $ANALYSIS_FAIL -gt 0 ]]; then
  VERDICT="ПРОБЛЕМЫ"
else
  VERDICT="УСПЕХ"
fi

{
  echo "🏁 СЕРИЯ $GROUP ЗАВЕРШЕНА"
  echo ""
  echo "IC: dwarf_rot_N1e5_k05, N=1e5, T=2, TimeBet=0.1, $PROCS процессов"
  echo "Суммарное время симуляций: $(fmt_min "$series_total_min")"
  echo "Анализ: $([[ $ANALYSIS_FAIL -eq 0 ]] && echo completed || echo $ANALYSIS_FAIL failed)"
  echo "Вердикт: $VERDICT"
  echo ""
  echo "Run | sigma | f | NI total | rho_core | slope | time"
  for i in "${!NAMES[@]}"; do
    name=${NAMES[$i]}
    f="/nbody/runs/$GROUP/$name/plots/summary_analysis.txt"
    if [[ ${STATUS[$i]:-1} -eq 0 && -f "$f" ]]; then
      rc_v=$(grep -oP 'Core density \\(r<[0-9.]+\\): \\K[0-9.e+-]+' "$f" | head -1)
      sl_v=$(grep -oP 'Inner log-slope.*: \\K[-0-9.]+' "$f" | head -1)
      ni_v=$(grep -oP 'NInteractions TOTAL: \\K[0-9]+' "$f" | head -1)
      echo "${name//_N1e5_T2/} | ${SIGMAS[$i]:-0} | ${DISSS[$i]:--} | ${ni_v:--} | ${rc_v:--} | ${sl_v:--} | $(fmt_min "${WALL_MIN[$i]:-0}")"
    else
      echo "${name//_N1e5_T2/} | FAILED"
    fi
  done
  echo ""
  echo "Лог: $LOG"
} > "$MSGFILE"
tg_send "$MSGFILE"

for png in "${NAMES[@]}"; do
  [[ -f "/nbody/runs/$GROUP/$png/plots/disk_edgeon.png" ]] && \
    tg_photo "disk_edgeon: $png" "/nbody/runs/$GROUP/$png/plots/disk_edgeon.png"
done

log "=== MATRIX COMPLETE (failed=$FAILED, verdict=$VERDICT) ==="
