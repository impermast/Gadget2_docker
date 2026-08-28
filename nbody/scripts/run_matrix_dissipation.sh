#!/usr/bin/env bash
# run_matrix_dissipation.sh — матрица CDM/SIDM/dSIDM (N=1e5, T=2) в группе
# runs/test_dissipation/. Первый прогон — тестовый dSIDM (σ=10, f=0.5):
# после него физический чек, при успехе — остальные 11. Финал: анализ
# run_full_test по всем + TG-сводка метрик + edge-on карты.
set -uo pipefail

export OMPI_MCA_hwloc_base_use_hwthreads_as_cpus=1
PROCS=10
IC=/nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5_k05.hdf5
TIME_MAX=2.0
TIME_BET=0.1
GROUP=test_dissipation
LOG=/nbody/runs/$GROUP/series.log
MSGFILE=/tmp/matrix_tg_msg.txt

# ТЕСТОВЫЙ мини-блок: не вся матрица, а только базовое сравнение
# CDM / упругий SIDM / dissipative SIDM с anti-sticking kick.
NAMES=(cdm_N1e5_T2 sidm10_N1e5_T2 dsidm10_f05_k15_N1e5_T2)
TYPES=(cdm sidm sidm)
SIGMAS=("" 10 10)
DISSS=("" "" 0.5)
KICKS=("" "" 15)

tg_send() {
  python3 -c "import sys;sys.path.insert(0,'/nbody/tg');from tg_notify import TgNotify;TgNotify().send_message(open('$1').read())" >/dev/null 2>&1 || true
}
tg_photo() {
  python3 -c "import sys;sys.path.insert(0,'/nbody/tg');from tg_notify import TgNotify;TgNotify().send_photo('$1','$2', parse_mode=None)" >/dev/null 2>&1 || true
}
log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
fmt_min() { local m=$1; echo "$((m / 60))h $((m % 60))m"; }
snap_count() { ls /nbody/runs/$GROUP/$1/output/snapshot_*.hdf5 2>/dev/null | wc -l; }

mkdir -p "/nbody/runs/$GROUP"
log "=== MATRIX START: ${#NAMES[@]} runs (procs=$PROCS) ==="

# Чистый тестовый старт: удаляем только каталоги run'ов текущего блока,
# чтобы не падать на повторном запуске после ручных/предыдущих прогонов.
for name in "${NAMES[@]}"; do
  rm -rf "/nbody/runs/$GROUP/$name"
done

cat > "$MSGFILE" <<EOF
🧪 TEST DISSIPATION BLOCK (N=1e5, T=2 Gyr) — 3 прогона
Группа: runs/$GROUP/
Состав: CDM + SIDM(σ=10) + dSIDM(σ=10, f=0.5, kick=15)
EOF
tg_send "$MSGFILE"

declare -a STATUS WALL_MIN
FAILED=0
for i in "${!NAMES[@]}"; do
  name=${NAMES[$i]}; type=${TYPES[$i]}; sigma=${SIGMAS[$i]}; diss=${DISSS[$i]}; kick=${KICKS[$i]}
  log "=== RUN START: $name (type=$type sigma=${sigma:-0} diss=${diss:--} kick=${kick:--}) ==="
  start_s=$(date +%s)

  cmd=(bash /nbody/scripts/run_sim.sh
       --name "$GROUP/$name" --type "$type"
       --time-max "$TIME_MAX" --time-bet "$TIME_BET"
       --ic-file "$IC" --mpi-procs "$PROCS")
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
❌ $name — ОШИБКА (exit $rc)
Лог: /nbody/runs/$GROUP/$name/run.log
EOF
    tg_send "$MSGFILE"
    continue
  fi

  log "=== RUN DONE: $name ($(fmt_min "$wall_min")) ==="
done

# ───────────────────────────── АНАЛИЗ ─────────────────────────────────────
cat > "$MSGFILE" <<EOF
🔬 Тестовый блок завершён. Запускаю анализ (run_full_test × 3)...
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
{
  echo "🏁 TEST DISSIPATION BLOCK ЗАВЕРШЕН"
  echo ""
  echo "Прогон | σ | f | ρ_core(r<2) | slope | NI"
  for i in "${!NAMES[@]}"; do
    name=${NAMES[$i]}
    f="/nbody/runs/$GROUP/$name/plots/summary_analysis.txt"
    if [[ ${STATUS[$i]:-1} -eq 0 && -f "$f" ]]; then
      rc_v=$(grep -oP 'Core density \\(r<[0-9.]+\\): \\K[0-9.e+-]+' "$f" | head -1)
      sl_v=$(grep -oP 'Inner log-slope.*: \\K[-0-9.]+' "$f" | head -1)
      ni_v=$(grep -oP 'NInteractions TOTAL: \\K[0-9]+' "$f" | head -1)
      echo "${name//_N1e5_T2/} | ${SIGMAS[$i]:-0} | ${DISSS[$i]:--} | $rc_v | $sl_v | $ni_v"
    else
      echo "${name//_N1e5_T2/} | FAILED"
    fi
  done
  echo ""
  echo "Edge-on карты: /nbody/runs/$GROUP/<run>/plots/disk_edgeon.png"
  echo "Лог: $LOG"
} > "$MSGFILE"
tg_send "$MSGFILE"

for png in cdm_N1e5_T2 sidm10_N1e5_T2 dsidm10_f05_k15_N1e5_T2; do
  [[ -f "/nbody/runs/$GROUP/$png/plots/disk_edgeon.png" ]] && \
    tg_photo "disk_edgeon: $png" "/nbody/runs/$GROUP/$png/plots/disk_edgeon.png"
done

log "=== MATRIX COMPLETE (failed=$FAILED) ==="
