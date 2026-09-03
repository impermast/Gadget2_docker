#!/usr/bin/env bash
# run_matrix_dissipation_focused_T5.sh — focused long-run dSIDM follow-up
# after the T=2 grid showed no robust disk signature but identified stable
# high-interaction candidates. Runs 5 simulations at N=1e5, T=5 on the same
# rotating dwarf IC, then performs final plots plus shape/thickness comparison.
set -uo pipefail

export OMPI_MCA_hwloc_base_use_hwthreads_as_cpus=1
PROCS=${PROCS:-8}
IC=/nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5_k05.hdf5
TIME_MAX=5.0
TIME_BET=0.1
GROUP=${GROUP:-test_dissipation_focused_T5}
LOG=/nbody/runs/$GROUP/series.log
MSGFILE=/tmp/focused_t5_tg_msg.txt
EXPECTED_SNAPS=51

NAMES=(
  cdm_N1e5_T5
  sidm10_N1e5_T5
  dsidm5_f005_k0_N1e5_T5
  dsidm10_f005_k0_N1e5_T5
  dsidm10_f01_k0_N1e5_T5
)
TYPES=(cdm sidm sidm sidm sidm)
SIGMAS=("" 10 5 10 10)
DISSS=("" "" 0.05 0.05 0.1)
KICKS=("" "" 0 0 0)
# Conservative T=5 estimates on 8 MPI processes, minutes.
EST_MIN=(45 65 65 85 115)

tg_send() {
  python3 -c "import sys;sys.path.insert(0,'/nbody/tg');from tg_notify import TgNotify;TgNotify().send_message(open('$1').read(), parse_mode=None)" >/dev/null 2>&1 || true
}

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
fmt_min() { local m=$1; echo "$((m / 60))h $((m % 60))m"; }
snap_count() { ls /nbody/runs/$GROUP/$1/output/snapshot_*.hdf5 2>/dev/null | wc -l; }

sum_est_min_from() {
  local start=$1 ratio=$2 total=0 i
  for ((i = start; i < ${#NAMES[@]}; i++)); do
    total=$((total + ${EST_MIN[$i]} * 60))
  done
  python3 -c "print(int($total * $ratio / 60))"
}

is_run_complete() {
  local name=$1 state=/nbody/runs/$GROUP/$name/run.state
  [[ -f "$state" ]] || return 1
  local status; status=$(grep -oP 'STATUS=\K[A-Z]+' "$state" 2>/dev/null)
  [[ "$status" == "COMPLETED" ]] || return 1
  local snaps; snaps=$(snap_count "$name")
  [[ "$snaps" -ge "$EXPECTED_SNAPS" ]]
}

mkdir -p "/nbody/runs/$GROUP"
log "=== FOCUSED T5 MATRIX START: ${#NAMES[@]} runs (procs=$PROCS) ==="

cat > "$MSGFILE" <<EOF
🚀 FOCUSED dSIDM T=5 MATRIX START

Группа: /nbody/runs/$GROUP/
IC: dwarf_rot_N1e5_k05, N=1e5, TimeMax=$TIME_MAX, TimeBet=$TIME_BET
Runs: CDM, SIDM10, dSIDM5 f=0.05, dSIDM10 f=0.05, dSIDM10 f=0.1
Процессов: $PROCS
Оценка суммарно: ~$(fmt_min "$(sum_est_min_from 0 1.0)")
EOF
tg_send "$MSGFILE"

declare -a STATUS WALL_MIN
FAILED=0
ratio=1.0
SERIES_START_S=$(date +%s)
COMPLETED_COUNT=0

for i in "${!NAMES[@]}"; do
  name=${NAMES[$i]}; type=${TYPES[$i]}; sigma=${SIGMAS[$i]}; diss=${DISSS[$i]}; kick=${KICKS[$i]}

  if is_run_complete "$name"; then
    STATUS[$i]=0
    WALL_MIN[$i]=0
    COMPLETED_COUNT=$((COMPLETED_COUNT+1))
    log "=== RUN SKIP (already completed): $name ==="
    continue
  fi

  if [[ -d "/nbody/runs/$GROUP/$name" ]]; then
    log "ABORT: existing but incomplete run directory: /nbody/runs/$GROUP/$name"
    log "Manual decision required: resume is only allowed for completed runs."
    exit 1
  fi

  log "=== RUN START: $name (type=$type sigma=${sigma:-0} diss=${diss:--} kick=${kick:--}) ==="
  start_s=$(date +%s)
  cmd=(bash /nbody/scripts/run_sim.sh
       --name "$GROUP/$name" --type "$type"
       --time-max "$TIME_MAX" --time-bet "$TIME_BET"
       --ic-file "$IC" --mpi-procs "$PROCS"
       --no-tg)
  [[ -n "$sigma" ]] && cmd+=(--sigma "$sigma")
  [[ -n "$diss" ]] && cmd+=(--dissipation "$diss")
  [[ -n "$kick" ]] && cmd+=(--kick "$kick")
  "${cmd[@]}" >> "$LOG" 2>&1
  rc=$?
  wall_min=$(( ($(date +%s) - start_s) / 60 ))
  STATUS[$i]=$rc
  WALL_MIN[$i]=$wall_min

  if [[ $rc -ne 0 ]]; then
    FAILED=$((FAILED+1))
    log "=== RUN FAILED: $name (rc=$rc, $(fmt_min "$wall_min")) ==="
    cat > "$MSGFILE" <<EOF
❌ $name упал за $(fmt_min "$wall_min")
Exit code: $rc
Снапшотов: $(snap_count "$name") / $EXPECTED_SNAPS
Лог: /nbody/runs/$GROUP/$name/run.log
EOF
    tg_send "$MSGFILE"
    continue
  fi

  COMPLETED_COUNT=$((COMPLETED_COUNT+1))
  if [[ ${EST_MIN[$i]} -gt 0 ]]; then
    ratio=$(python3 -c "print(round(0.5 * $ratio + 0.5 * ($wall_min / ${EST_MIN[$i]}), 3))")
  fi
  n_left=$(( ${#NAMES[@]} - COMPLETED_COUNT ))
  eta_left=$(sum_est_min_from $((i + 1)) "$ratio")
  elapsed_min=$(( ($(date +%s) - SERIES_START_S) / 60 ))
  next_name=""
  [[ $n_left -gt 0 ]] && next_name=${NAMES[$((i + 1))]}

  cat > "$MSGFILE" <<EOF
✅ $name завершён за $(fmt_min "$wall_min")
Снапшотов: $(snap_count "$name") / $EXPECTED_SNAPS

Серия: $GROUP
Прогресс: $COMPLETED_COUNT / ${#NAMES[@]}
Суммарно идёт: $(fmt_min "$elapsed_min")
Осталось: $n_left (~$(fmt_min "$eta_left"))
EOF
  [[ -n "$next_name" ]] && echo "Следующий: $next_name" >> "$MSGFILE"
  tg_send "$MSGFILE"
  log "=== RUN DONE: $name ($(fmt_min "$wall_min")), ratio=$ratio ==="
done

cat > "$MSGFILE" <<EOF
🔬 FOCUSED T=5 simulations finished. Starting final analysis:
- run_full_test.py for each successful run
- analyze_series.py shape/thickness diagnostics
- compare_shape_series.py group report
EOF
tg_send "$MSGFILE"
log "=== ANALYSIS PHASE START ==="

ANALYSIS_FAIL=0
SUCCESS_NAMES=()
for i in "${!NAMES[@]}"; do
  name=${NAMES[$i]}
  if [[ ${STATUS[$i]:-1} -ne 0 ]]; then
    log "ANALYSIS SKIPPED: $name (run failed)"
    continue
  fi
  SUCCESS_NAMES+=("$name")
  log "--- run_full_test: $name ---"
  python3 /nbody/scripts/plot_scripts/run_full_test.py \
    --run-root "/nbody/runs/$GROUP/$name" >> "$LOG" 2>&1 || ANALYSIS_FAIL=$((ANALYSIS_FAIL+1))
  log "--- analyze_series: $name ---"
  python3 /nbody/scripts/check_simulations/analyze_series.py \
    --run-root "/nbody/runs/$GROUP/$name" \
    --outdir "/nbody/runs/$GROUP/$name/partial_analysis" \
    --max-frames 10 >> "$LOG" 2>&1 || ANALYSIS_FAIL=$((ANALYSIS_FAIL+1))
done

if [[ ${#SUCCESS_NAMES[@]} -gt 0 ]]; then
  log "--- compare_shape_series ---"
  python3 /nbody/scripts/check_simulations/compare_shape_series.py \
    --group-root "/nbody/runs/$GROUP" \
    --runs "${SUCCESS_NAMES[@]}" \
    --outdir "/nbody/runs/$GROUP/shape_compare" \
    --tg >> "$LOG" 2>&1 || ANALYSIS_FAIL=$((ANALYSIS_FAIL+1))
fi

total_min=$(( ($(date +%s) - SERIES_START_S) / 60 ))
if [[ $FAILED -gt 0 ]]; then
  VERDICT="ОШИБКА"
elif [[ $ANALYSIS_FAIL -gt 0 ]]; then
  VERDICT="ПРОБЛЕМЫ"
else
  VERDICT="ANALYSIS_COMPLETE"
fi

cat > "$MSGFILE" <<EOF
🏁 FOCUSED dSIDM T=5 MATRIX COMPLETE

Группа: /nbody/runs/$GROUP/
Суммарное время: $(fmt_min "$total_min")
Run failures: $FAILED
Analysis failures: $ANALYSIS_FAIL
Вердикт: $VERDICT

Shape report: /nbody/runs/$GROUP/shape_compare/shape_summary.txt
Лог: $LOG
EOF
tg_send "$MSGFILE"
log "=== FOCUSED T5 MATRIX COMPLETE (failed=$FAILED, analysis_fail=$ANALYSIS_FAIL, verdict=$VERDICT) ==="