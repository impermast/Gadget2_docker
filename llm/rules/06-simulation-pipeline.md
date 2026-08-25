# Simulation pipeline rules

The user often wants tasks like:

"Create a simulation with N particles and SIDM cross-section 10 based on galaxy initial conditions, run it, then visualize the result."

For such tasks, use this controlled pipeline.

## Stage 1. Interpret request

Extract:

- simulation type: CDM or SIDM;
- particle number;
- self-interaction cross-section;
- initial condition source;
- target runtime length;
- output cadence;
- visualization type;
- whether this is a quick test or production run.

If a parameter is missing, make a conservative default and state it.

## Stage 2. Inspect templates

Read only relevant small files:

- run script;
- parameter template;
- config file;
- IC generation script;
- visualization script.

Do not read snapshots or outputs.

## Stage 3. Create isolated run

Create a new run folder, for example:

`nbody/runs/YYYYMMDD_sidm_sigma10_N10000/`

Inside it, keep:

- copied parameter file;
- copied config metadata;
- run command;
- logs;
- output directory;
- visualization output.

Do not overwrite baseline files.

## Stage 4. Patch configs

Modify copied files only.

Record:

- particle number;
- cross-section;
- IC file;
- output directory;
- random seed if used;
- relevant compile flags;
- run command.

## Stage 5. Dry check

Before running:

- verify paths exist;
- verify output directory is new;
- verify parameter file references correct IC;
- verify parameter file references correct output path;
- show final command.

## Stage 6. Run

For quick tests, run after user request.

For long production runs, ask explicit confirmation.

Capture log to a file, e.g. `run.log`.

## Stage 7. Validate

After run:

- check exit status;
- check whether snapshots/output files exist;
- inspect only small logs and filenames;
- do not open large binary outputs unless needed.

## Stage 8. Visualize

Run the selected visualization script on produced outputs.

Generated images should go to:

`nbody/runs/<run_name>/plots/`

## Stage 9. Report

Report:

- what was changed;
- where the run folder is;
- exact command used;
- whether the run completed;
- where outputs are;
- where plots are;
- any warnings.

## Stage 10. Update memory

Update:

- `llm/memory-bank/activeContext.md`
- `llm/memory-bank/progress.md`
- `llm/memory-bank/experimentLog.md`