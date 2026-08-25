# GIZMO workflow rules

For GIZMO tasks, inspect in this order:

1. `nbody/gizmo_test/run_gizmo.sh`
2. selected parameter file:
   - `nbody/gizmo_test/gizmo_cdm.param`
   - `nbody/gizmo_test/gizmo_sidm.param`
   - or a new copied param file
3. runtime/generated param file if relevant:
   - `nbody/gizmo_test/.gizmo_run.param`
4. config/build files:
   - `nbody/gizmo_test/Config_cdm_sidm.sh`
   - `nbody/gizmo_test/GizmoMakefile`
   - `nbody/gizmo_test/Makefile.systype`
5. initial-condition script if relevant:
   - `nbody/gizmo_test/generate_ics.sh`

Rules:

- Never overwrite baseline config/param files directly for a new experiment.
- Create a new run directory or new parameter file for each experiment.
- Put outputs into a unique output directory.
- Do not open HDF5 snapshots unless explicitly requested.
- Prefer scripts that create reproducible run folders.
- The config `Config_cdm_sidm.sh` sets `DM_SIDM=8` (particle type 3) — remember this when editing.