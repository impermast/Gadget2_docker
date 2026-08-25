# Project Brief

This repository provides a Dockerized environment for GADGET-2, GIZMO, and GalIC scientific simulations.

Primary goal:

- maintain a reproducible Docker-based workflow;
- keep system dependencies and third-party source trees inside the image;
- keep user-editable simulation configs, run scripts, parameter files, and analysis scripts in `nbody/`;
- support controlled reproducible simulations through isolated run folders.

Main boundary:

- `/opt` inside the container is the stable software layer;
- `/nbody` is the mounted user workspace from the host repository;
- `llm/` stores agent rules and memory; operational simulation/plotting protocols are exposed as agent skills (`gizmo-sim`, `make-plots` in `skills/`).

Agent goal:

- help debug and improve scripts, parameter files, build wrappers, and documentation;
- create reproducible simulation run folders;
- launch controlled simulations only when requested;
- launch visualization scripts after runs;
- avoid reading large simulation data;
- avoid destructive commands and long simulations without explicit approval.