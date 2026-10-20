# Workflow: change shared visual style

This route is for cross-cutting design changes (palette/theme, fonts, line weights, grid, sizing, export defaults) that should apply consistently across the plot pool. Do not tune individual figures one by one.

1. Inspect `nbody/scripts/analysis/style.py` and trace how the relevant `PlotSettings` fields reach `BasePlot`/plot renderers. Treat this module as the central visual policy.
2. Identify whether the requested visual property is already centralized. If so, propose or change the shared setting only. If plots override it locally, inventory those overrides and determine whether they are intentional semantics (e.g. sequential/diverging data maps, readability of dense panels) or accidental styling duplication.
3. Keep scientific encoding intact: do not change normalization, sign, thresholds, data ranges, units, or comparisons under the guise of theme work. Color-map roles (categorical/sequential/diverging) must remain fit for the data semantics and accessible.
4. Do not add per-plot exceptions just to make one image look nicer. If a true exception is necessary, document why and keep it minimal. If common settings cannot control a visual feature, first identify the missing shared abstraction rather than patching each plot separately.
5. For an implementation request, inspect current dirty state and preserve unrelated edits. Make the smallest central change, run focused rendering/math/guard tests, and inspect representative plots from each affected family. Do not regenerate/overwrite existing scientific outputs without explicit authorization; use synthetic test fixtures where possible.
6. Report the central setting changed, affected plot families, exceptions, tests, and any figures not regenerated. A style change is not complete merely because one sample plot looks good.
