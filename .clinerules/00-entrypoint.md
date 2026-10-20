# Cline entrypoint

# Cline entrypoint

Read repository-root `AGENTS.md` first, then `llm/PROJECT.md`, `llm/PLAN.md`, `llm/ACTIVE.md`, and `llm/MEMORY.md`. Load only the relevant skill under `.agents/skills/`, then retrieve specific canonical evidence or a `llm/records/` document only when needed. Never recursively load `llm/`; never auto-load `llm/sessions/` or `llm/completed-plans/`.

`llm/records/` is for important durable knowledge, not an activity journal. By default do not create a record; follow the gate in `llm/PROJECT.md`.

Communicate in Russian. Do not open large simulation data, snapshots, HDF5, binaries, plots, or generated outputs unless specifically needed. Do not run long simulations, Docker rebuilds, install packages, destructive cleanup, commit, or push without explicit approval. For simulation tasks, use isolated run directories under `nbody/runs/`; never overwrite baseline configs or outputs.