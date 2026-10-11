#!/usr/bin/env bash
# Run the two approved M5, T=5, k08 SIDM jobs sequentially.
set -euo pipefail

CONTAINER=gadget-gizmo
TIME_LIMIT=14400
PYTHON=python3
DRY_RUN=0
LOG_DIR=${M5_QUEUE_LOG_DIR:-/tmp/gadget2-m5-queue}
RUN_ROOT=/nbody/runs
GROUP=dsidm_spin_k08_transition
GATE=/nbody/scripts/conference/post_run_gate.py

RUNS=(
  dsidm_s2p5_D0p25_N1e5_T5_k08
  dsidm_s2p5_D0p50_N1e5_T5_k08
)
DISS=(0.25 0.50)

usage() {
  echo "Usage: $0 [--dry-run] [--container NAME] [--time-limit SECONDS] [--python PATH] [--log-dir DIR]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --container) CONTAINER=$2; shift 2 ;;
    --time-limit) TIME_LIMIT=$2; shift 2 ;;
    --python) PYTHON=$2; shift 2 ;;
    --log-dir) LOG_DIR=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

docker_cmd=(docker exec "$CONTAINER")
preflight() {
  if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -qx true; then
    echo "ERROR: container is not running: $CONTAINER" >&2
    return 1
  fi
  local processes
  processes=$("${docker_cmd[@]}" ps -eo args 2>/dev/null || true)
  if printf '%s\n' "$processes" | grep -Eiq '(^|/)(gizmo|gadget|mpirun|mpiexec)([[:space:]]|$)'; then
    echo "ERROR: an active solver/MPI process is already present in $CONTAINER" >&2
    printf '%s\n' "$processes" >&2
    return 1
  fi
}

if [[ "$DRY_RUN" -eq 0 ]]; then
  preflight
  mkdir -p "$LOG_DIR"
else
  echo "[DRY-RUN] container preflight skipped; no simulation will be started"
fi

for i in "${!RUNS[@]}"; do
  run_id=${RUNS[$i]}
  diss=${DISS[$i]}
  run_name="$GROUP/$run_id"
  run_root="$RUN_ROOT/$run_name"
  cmd=(bash /nbody/scripts/run_sim.sh
    --name "$run_name" --type sidm --sigma 2.5 --dissipation "$diss"
    --time-max 5 --time-bet 0.1 --ic-file /nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5_k08
    --first-snapshot 0 --mpi-procs 8 --max-step .005 --kick 0
    --time-limit "$TIME_LIMIT" --skip-viz --no-tg)
  echo "RUN $run_id"
  printf 'COMMAND docker exec %q %q' "$CONTAINER" "${cmd[0]}"
  printf ' %q' "${cmd[@]:1}"
  echo

  if [[ "$DRY_RUN" -eq 1 ]]; then
    continue
  fi
  if "${docker_cmd[@]}" test -e "$run_root"; then
    echo "ERROR: refusing pre-existing target run directory: $run_root" >&2
    exit 1
  fi

  solver_log="$LOG_DIR/${run_id}.solver.log"
  echo "SOLVER_LOG $solver_log"
  set +e
  "${docker_cmd[@]}" "${cmd[@]}" >"$solver_log" 2>&1
  solver_rc=$?
  set -e
  echo "RUN $run_id exit_code=$solver_rc"
  if [[ "$solver_rc" -ne 0 ]]; then
    echo "SOLVER_LOG_TAIL $run_id" >&2
    tail -n 40 "$solver_log" >&2 || true
  fi

  set +e
  gate_json=$("${docker_cmd[@]}" "$PYTHON" "$GATE" --run-root "$run_root" --expected-time 5 --min-snapshots 1 2>&1)
  gate_rc=$?
  set -e
  echo "GATE $run_id $gate_json"
  if [[ "$gate_rc" -ne 0 ]]; then
    echo "ERROR: post_run_gate failed; aborting queue" >&2
    exit "$gate_rc"
  fi
  verdict=$(printf '%s' "$gate_json" | "$PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["verdict"])')
  if [[ "$solver_rc" -ne 0 || "$verdict" != completed ]]; then
    echo "ERROR: run $run_id not completed (solver_rc=$solver_rc, verdict=$verdict); aborting queue" >&2
    exit 1
  fi
done

echo "Queue finished: ${#RUNS[@]} runs completed."
