# Workflow rules

Use Plan mode first when:

- the task affects multiple files;
- the simulation setup is unclear;
- initial conditions must be generated or modified;
- GIZMO/GADGET/GalIC configs must be changed;
- Docker/build behavior is involved;
- the task may be expensive.

Use Act mode when:

- the user has approved the plan;
- affected files are known;
- output directory is chosen;
- commands are clear;
- checkpoints are enabled.

After meaningful work, update:

- `llm/memory-bank/activeContext.md`
- `llm/memory-bank/progress.md`
- `llm/memory-bank/experimentLog.md` if a simulation or analysis was run
  (the `gizmo-sim` and `make-plots` skills append their run summaries to it).

Operational step-by-step protocols live in the repo skills `gizmo-sim` and `make-plots` under `skills/`, not in this folder.

Do not dump raw logs into memory. Store concise conclusions, paths, parameters, and result status.

## Git policy (branches and commits)

Branch model:

- `master` — stable code. The agent never pushes to `master` directly.
- `agent/dev` — the single long-lived agent branch. Do NOT create a new branch
  per task; all agent work happens in `agent/dev`.

Commit rules:

- Commit template: `llm/gitmessage.txt` (enabled via
  `git config commit.template llm/gitmessage.txt`). Fields RUN / TEST / RESULT
  link git history with `llm/memory-bank/experimentLog.md`.
- Small atomic commits, types: `feat|fix|refactor|test|docs|chore`.
- Commits require user approval per `01-safety.md`; pushing `agent/dev`
  is allowed after notifying the user.

Merge procedure (`agent/dev` → `master`, executed by the user or by the agent
on explicit request):

```bash
git checkout master
git merge --no-ff agent/dev           # bring in code changes
git rm -r --cached llm/               # untrack llm/ on master
git checkout agent/dev -- .gitignore  # restore master .gitignore (ignores llm/)
# fix .gitignore if needed so it matches master state, then:
git commit -m "chore: sync agent/dev, drop llm tracking"
```

Rationale: `.gitignore` differs between branches — on `agent/dev` `llm/` is
tracked (bot process history), on `master` it stays untracked.

## Testing policy

- Fast unit tests live in `tests/` and run with `.venv/bin/python -m pytest tests/ -q`.
- Tests are split into marker groups (`pytest.ini`): `math` (level 1 loaders
  math) and `golden` (level 2 answer tests). Run a single group with
  `-m <group>`. CI runs each group as a separate matrix job.
- The full suite must stay fast (<30 s): synthetic HDF5 fixtures only,
  no simulations. The agent may run pytest freely without confirmation.
- Golden/reference values (`tests/golden/values.json`) are regenerated ONLY
  deliberately, via `python tests/make_golden.py`, when loaders math changes
  on purpose; the reason must be recorded in `tests/golden/README.md`.
- Long smoke simulations of GIZMO/GADGET remain manual procedures via the
  `gizmo-sim` skill and are NOT part of pytest.
- Auto-run: pre-commit hook `githooks/pre-commit` runs the suite before every
  commit. Enable after fresh clone with:
      git config core.hooksPath githooks
- CI: `.github/workflows/tests.yml` runs the same suite on every push/PR
  (GitHub Actions).