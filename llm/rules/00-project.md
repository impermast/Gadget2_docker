# Project rules

- Explain to the user in Russian.
- This is a Dockerized scientific simulation workflow for GADGET-2, GIZMO, and GalIC.
- The project is used to study how dark matter self-interactions affect halo and subhalo morphology, density profiles, clump survival, relaxation, and possible indirect-signature-relevant structures (dark disk, dark bars, clumps, spirals). 
- A typical task may involve creating or modifying galaxy/halo initial conditions, running CDM or SIDM simulations, changing self-interaction cross-section parameters, and visualizing the resulting particle distribution.
- The agent must preserve physical consistency when modifying simulations: particle number, mass resolution, gravitational softening, time-step parameters, output cadence, initial-condition paths, unit conventions, and SIDM cross-section parameters must be checked together.
- If a requested physical parameter is ambiguous, the agent should not guess silently. It should state the assumed convention and ask for confirmation if the ambiguity can change the result.
- The repository root should be the VS Code workspace root.
- The Docker image contains stable scientific dependencies and third-party source trees.
- User-editable simulation files should live mainly in `nbody/`.
- Detailed agent files live in `llm/`.
- Prefer small tracked text files over generated files.
- Do not read large simulation outputs unless the user explicitly requests a specific file.
- Do not edit external/vendor source trees under `/opt` unless explicitly requested.
- Before changing Dockerfile, inspect README, startup scripts, run scripts, config files, and parameter files.
- Note: `nbody/gadget_test/run_gadget.sh` may reference `/workspace/Gadget-2.0.7/Gadget2` instead of `/opt/gadget-2.0.7` — verify the actual path before running.