# Workflow: inspect existing figures and analysis outputs

Use when the user asks what an already-generated figure/report shows, or asks to check whether expected outputs exist. Do not regenerate as a side effect.

1. Locate the canonical artifact using `AnalysisPaths` conventions and the run/campaign identifier. If the target is ambiguous, ask instead of searching through large generated trees.
2. Inspect only the specifically requested artifact. For images, use image viewing if available; for text/CSV, read only the relevant report/rows. Do not open snapshots/HDF5 directly.
3. Distinguish visual observations from scientific conclusions. Check the plot's registry summary, data source and configuration as needed; identify units, time/snapshot and input runs where evidence is available. If provenance or metadata is absent, say unknown.
4. Do not infer physical validity from a plot alone. Incomplete/pathological runs require the applicable `check-run` workflow and must be labeled preliminary; do not silently initiate that separate check.
5. Report what was inspected and any limitations. No files should be created or modified in this workflow.
