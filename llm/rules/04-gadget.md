# GADGET-2 workflow rules

For GADGET-2 tasks, inspect in this order:

1. `nbody/gadget_test/run_gadget.sh`
2. selected parameter file, usually `nbody/gadget_test/lcdm_gas.param`
3. `nbody/gadget_test/Makefile`
4. relevant small Python helper scripts

Rules:

- Do not open `.dat`, snapshot, graph, or generated output files unless explicitly requested.
- Do not run full GADGET simulations without explicit confirmation.
- Do not edit `/opt/gadget-2.0.7` directly unless explicitly requested.
- Prefer isolated run folders under `nbody/runs/`.
- Note: `run_gadget.sh` may reference `/workspace/Gadget-2.0.7/Gadget2` — verify if this path is correct for your container or if it should be `/opt/gadget-2.0.7`.