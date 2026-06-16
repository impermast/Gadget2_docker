# GalIC to GIZMO Pipeline

Goal:

Generate or select GalIC galaxy initial conditions and use them as input for a GIZMO simulation.

## Canonical tools

- `bash /nbody/scripts/generate_ics.sh --config <config.json>` — генерация IC через GalIC
- `bash /nbody/scripts/run_sim.sh --name <name> --type cdm|sidm` — запуск GIZMO

## Protocol

1. Prepare or reuse a JSON config file for `generate_ics.sh`.
2. Run `generate_ics.sh`:
   ```bash
   bash /nbody/scripts/generate_ics.sh --config /nbody/ics/my_config.json
   ```
3. Check output: `nbody/ics/<run_name>/<run_name>.hdf5`
4. Run simulation:
   ```bash
   bash /nbody/scripts/run_sim.sh \
     --name <run_name> \
     --type cdm|sidm \
     --time-max 5.0 \
     --ic-file /nbody/ics/<run_name>/<run_name>
   ```
5. Check `run_dir/snapshot_check.txt` and `run_dir/experiment.md`
6. Optionally run visualization.
7. Update experiment log.

## JSON config format

```json
{
  "run_name": "my_cdm",
  "output_dir": "/nbody/ics/my_cdm",
  "galic_param": "nbody/GalIC/halo_nfw_ics.param",
  "components": [
    {"name": "dm", "n": 10000, "cc": 10, "v200": 200, "map_to": 3, "sigma": 0}
  ]
}
```

### Fields

| Field | Description |
|-------|-------------|
| `run_name` | Unique name for this IC set |
| `output_dir` | Absolute path inside `/nbody/ics/` |
| `galic_param` | Path to GalIC param template (relative to `/nbody`) |
| `components` | Array of components to generate |

### Component fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Component name (used for directories and filenames) |
| `n` | yes | Number of particles |
| `cc` | yes | Halo concentration (CC parameter) |
| `v200` | yes | Circular velocity v200 in km/s |
| `map_to` | yes | Target PartType (1, 3, etc.) |
| `sigma` | no | SIDM cross-section (for info only, not used in IC generation) |
