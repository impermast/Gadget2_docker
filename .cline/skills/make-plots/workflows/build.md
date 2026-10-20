# Workflow: render registered plots

1. Establish whether the input is an IC, prerun, one production run, or a run group/campaign. For supported plots, read `nbody/analysis/REGISTRY.md` and choose the entry by meaning and required input. Use that entry's runner and config keys.
2. Resolve exact input run roots and, for campaigns, the intended stable campaign/member names. Never create a fresh timestamp/random suffix merely to bypass an existing output collision. If the user has not specified a necessary campaign label, ask or propose one before rendering.
3. Determine the runner's exact CLI from the skill's canonical runner examples and, if uncertain, inspect that runner's argument parser. Do not infer arguments from another runner. Campaign plots may be split among profile, morphology, and diagnostic runners. For `make_campaign_plots.py`, list positional run paths before `--labels`.
4. Predict output paths using the registry filename and canonical layout from `AnalysisPaths`:
   - `analysis/ic/<ic>/`
   - `analysis/prerun/<run>/`
   - `analysis/core/<run>/`
   - `analysis/campaigns/<campaign>/<member>/`
   Root is `NBODY_ANALYSIS_ROOT` when set, otherwise `/nbody/analysis` in the container.
5. Check whether the requested canonical output files already exist. If they do, stop before invoking the runner and ask whether the user wants those files inspected/reused or explicitly regenerated. Do not make duplicate copies/directories to preserve versions; versioning/archive policy is not implicit.
6. Run only the canonical runner in `docker exec gadget-gizmo`, unless the user requests a read-only plan or the container is unavailable. Do not use custom scripts, `--outdir`, or direct Matplotlib code.
7. Verify expected files exist and are non-empty; for GIFs, verify more than one frame. Report actual paths, sizes, warnings/skips, command, and whether outputs were generated. Never interpret successful rendering as scientific validation.

### Canonical runner families

- IC: `runners/make_ic_plots.py`
- prerun: `runners/make_prerun_plots.py`
- one production run: `runners/make_run_plots.py`
- campaign profile comparisons: `runners/make_campaign_plots.py`
- campaign morphology: `runners/make_campaign_morphology_plots.py`
- campaign diagnostics: `runners/make_campaign_diag_plots.py`

The registry is authoritative for which plot belongs to which runner. Confirm exact CLI flags in the selected runner; do not use old examples from memory.
