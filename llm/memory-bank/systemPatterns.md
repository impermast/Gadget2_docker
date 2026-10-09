# System Patterns

Repository root:

- `Dockerfile`: builds the image and installs dependencies and third-party codes.
- `run_docker_gui_linux.sh`: starts/reuses the Docker container and mounts local `nbody/` to `/nbody`.
- `README.md`: source of truth for intended workflow.
- `nbody/`: user-editable simulation workspace.
- `llm/`: AI-agent rules and persistent memory; operational step-by-step protocols live in repo skills (`.cline/skills/gizmo-sim`, `.cline/skills/make-plots`, `.cline/skills/check-run`). Tracked ONLY on branch `agent/dev`.
- `tests/`: fast pytest suite (synthetic HDF5 fixtures + golden answer tests); no simulations inside.
- `githooks/pre-commit`: auto-runs pytest before each commit (enable via `git config core.hooksPath githooks`).
- `.github/workflows/tests.yml`: GitHub Actions CI — same suite on every push/PR, with junit statistics table in Step Summary.
- `pytest.ini`: pytest config (testpaths=tests).
- `llm/gitmessage.txt`: commit message template (RUN/TEST/RESULT fields).

Container layout:

- `/opt/gsl`
- `/opt/fftw`
- `/opt/glio`
- `/opt/gadget-2.0.7`
- `/opt/gizmo-public`
- `/opt/GalIC`
- `/nbody`: mounted from host `./nbody`.
- `/nbody/analysis/`: canonical analysis output/catalog, curated presentation
  assets, and migrated historical exports; host directory may be root-owned, so use the
  writable bind-mounted container for migration/registry operations when needed.

Workflow pattern:

1. Build Docker image if needed.
2. Edit configs/scripts/params on host or inside Dev Container.
3. Start or use the container.
4. Run simulations through the `gizmo-sim` skill: it creates an isolated folder under `nbody/runs/`, copies baseline params/configs via the `run_sim.sh` wrapper, modifies only run-specific copies, runs a controlled simulation, saves logs/outputs/plots in the run folder, and appends a summary to `llm/memory-bank/experimentLog.md`.
5. Visualization goes through the `make-plots` skill and the canonical
   `nbody/scripts/analysis/` package; `nbody/analysis/REGISTRY.md` is the generated
   catalog. `presentations/` stores curated assets only (no presentation runner).
6. Code changes are validated with the fast test suite (`pytest tests/ -q`,
   auto-run by the pre-commit hook on every commit) and committed on
   `agent/dev` using the commit template; CI re-checks on push.
7. Update `llm/memory-bank/experimentLog.md` if it was not updated by the skills.