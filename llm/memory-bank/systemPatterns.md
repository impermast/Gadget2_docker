# System Patterns

Repository root:

- `Dockerfile`: builds the image and installs dependencies and third-party codes.
- `run_docker_gui_linux.sh`: starts/reuses the Docker container and mounts local `nbody/` to `/nbody`.
- `README.md`: source of truth for intended workflow.
- `nbody/`: user-editable simulation workspace.
- `llm/`: AI-agent rules and persistent memory; operational step-by-step protocols live in the repo skills (`skills/gizmo-sim`, `skills/make-plots`).

Container layout:

- `/opt/gsl`
- `/opt/fftw`
- `/opt/glio`
- `/opt/gadget-2.0.7`
- `/opt/gizmo-public`
- `/opt/GalIC`
- `/nbody`: mounted from host `./nbody`.

Workflow pattern:

1. Build Docker image if needed.
2. Edit configs/scripts/params on host or inside Dev Container.
3. Start or use the container.
4. Run simulations through the `gizmo-sim` skill: it creates an isolated folder under `nbody/runs/`, copies baseline params/configs via the `run_sim.sh` wrapper, modifies only run-specific copies, runs a controlled simulation, saves logs/outputs/plots in the run folder, and appends a summary to `llm/memory-bank/experimentLog.md`.
5. Visualization goes through the `make-plots` skill.
6. Update `llm/memory-bank/experimentLog.md` if it was not updated by the skills.