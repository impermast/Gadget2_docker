# RUN_STATE

Updated UTC: 2026-10-11

Campaign ID / spec revision:
- `conference_2026_dsidm`
- `llm/CODEX_AUTONOMOUS_PROMPT.md` sha256 `100e8f687243c674cd29f3c2b7ab0fcf638d7360a52d9b9e64c8607b591e5ce0`
- `llm/CONFERENCE_TWO_WEEK_PLAN.md` sha256 `cdb2e21cf2dc2fe9614cbee57bc85fcb82577dcd31b0247f3b1f8f6b04252e8b`
- `llm/implementation_plan.md` sha256 `39d9b83a50786ae220354b844461a43ef39a6b42092153942019a1dc9a06882c`

Orchestration policy (current user override):
- At most one live subagent at a time.
- Delegate substantive bounded tasks to `gpt-5.6-luna` with reduced
  reasoning effort (`low`); wait for completion before issuing another task.
- The root agent independently checks and accepts or rejects every result
  before continuing. A rejected result is returned to the same agent for a
  bounded correction; no parallel delegation is allowed.

Branch / HEAD / initial dirty paths / owned changes:
- Branch: `agent/dev`; current local HEAD includes accepted M7 evidence commit
  `5924b52`; last accepted data checkpoint: `be092e3`.
- Plan files are campaign-owned specifications; their current hashes are
  recorded above and their checkpoint/push workflow is synchronized below.

Deadline / talk requirements / assumptions:
- Conference date is unknown; use relative D-14…D-0 only.
- Assumed talk duration: 15 minutes; language: Russian; audience: physical.
- These are assumptions pending one user clarification; no calendar deadline is
  claimed.

Permissions: action, scope, source of approval, remaining budget
- Source: explicit campaign-start request for M0 and orchestration by the root
  agent.
- Allowed now: local text/code edits, synthetic and targeted tests, bounded
  inspection/post-processing of existing data, and M4 implementation/review.
- Without a fresh explicit approval: no new simulations, no GIZMO solver
  validation, no sigma/m=5 runs, no Telegram/external messages. Local
  stage-checkpoint commits are explicitly approved for this campaign. Pushes
  require confirmation of the exact remote/ref by the safety gate; the current
  M7 commit is local and `push_pending`.
- Remaining budget: no heavy-run budget approved; no simulation was launched.

Capabilities: container, tools, communication, rendering/export
- Host `.venv/bin/python` is executable, Python 3.12.3. Container
  `gadget-gizmo` is running (`Up 2 hours` at the check); read-only Docker
  inspection required host Docker API approval. Its `/nbody` mount maps the
  workspace `nbody`, and `/opt/gizmo-public/GIZMO` is executable (384264 bytes).
- `/nbody/scripts/run_sim.sh`, `mpirun`, `python3`, and `bash` are present in
  the container. Existing ICs are present as
  `nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5_k05.hdf5` and `_k08.hdf5` (also
  visible under `/nbody/ics/...`); the wrapper strips an optional `.hdf5`
  suffix when resolving them.
- Baseline command: `.venv/bin/python -m pytest tests/ -q`; result: exit 0,
  51 passed, 1 warning about an empty `presentations` registry block, elapsed
  9.846 s. This was run before any M0 file edits.
- No host or container `mpirun`, `mpiexec`, `GIZMO`/`gizmo`, or `run_sim.sh`
  process was found at the preflight check.
- Communication: current session is available; Telegram is not permitted and
  was not used. No external messages were sent.
- Conference package directory write permission was corrected with `g+rwX`;
  canonical manifest, series index, and campaign summary are accepted outputs.
- Resources at check: 16 online CPUs; load 1.54/0.68/0.41; RAM 14 GiB total,
  10 GiB available; swap 1.9 GiB with 768 KiB used; workspace filesystem
  232 GiB total, 183 GiB used, 37 GiB available (84%), inode use 12%.
- Rendering/export: `pdftoppm` and `pdfinfo` available for PDF inspection,
  `libreoffice`/`soffice` available for office/slide conversion, `xdg-open`
  available; built-in `view_image` successfully confirmed PNG visual review
  on an existing figure. Dedicated `feh`/`eog`/ImageMagick, `pandoc`, `marp`,
  `quarto`, browser exporters, `pypdf`, and `python-pptx` were not found;
  dedicated binaries are not needed for PNG review. The four new M7 PNGs were
  rendered and independently inspected with `view_image`; PDF/slide export
  remains a later check. Background
  execution/waiting primitives `nohup`, `setsid`, and `timeout` are present;
  a shell background/wait smoke check passed in 0.103 s.

Milestones: M0..M8 -> pending | in_progress | done | blocked | deferred
- M0 `done` — preflight, baseline, permissions, and initial state recorded;
  checkpoint `5503e8e`.
- M1 `done` — manifest code/tests verified; 11 old runs inventoried (10
  completed, 1 incomplete; 9 healthy, 2 pathological; metrics 6 complete,
  1 partial, 4 missing); checkpoint `10b554c`.
- M2 `done` — Jz/mass/frame implementation and 28 targeted tests verified;
  intentional rotation-frame migration is documented by the delegated branch;
  combined implementation checkpoint `49cbb17`.
- M3 `done` — 20 tests and deterministic 15-row validation CSV verified;
  source audit hashes recorded; solver experiment remains not validated;
  checkpoint `d8934a3`.
- M4 `done (partial/deferred)` — bounded-memory sync/metadata and explicit
  late-time summaries are integrated and tested. A pilot plus eight safe
  existing series produced 313 metric rows; two large/pathological logs remain
  explicitly deferred by the resource gate. Data checkpoint `d161e84`.
- M6 `done (partial/deferred)` — canonical 11-row manifest, explicit 9-row
  series index, 11-row campaign summary and metadata accepted at `be092e3`;
  two deferred series are visible as missing coverage.
- M5 `pending`; M7 `in_progress` — talk drafts are at `b76500e`, figures and
  claims/evidence package at `5924b52`; editable slide integration, export,
  final visual freeze, and rehearsal remain pending; M8 `pending`.

Current task / acceptance check:
- M0–M6 acceptance evidence is recorded above. M4 code/data and scoped/full
  tests passed; the pilot and eight safe real-series runs were independently
  checked by the root agent. Current task: insert the accepted figures and
  claim locators into an editable slide source, then perform export/visual and
  rehearsal checks. No new simulation or solver validation is implied.

Processes: run_id, exact command, PID/job ID, started_at, log, limit, owner
- No campaign process. Preflight process scan found no matching host/container
  compute process; no PID/job/log/limit applies. Owner: none.

Artifacts: path, inputs, analysis version, last successful validation
- `llm/RUN_STATE.md`: inputs are the three plan files, repository state, and
  read-only capability checks; M0 baseline is the last validation.
- `llm/CODEX_BACKLOG.md`: M0 capability/resource findings only; no simulation
  or analysis artifact was generated.
- `nbody/analysis/presentations/conference_2026/m4_pilot/`: one accepted
  healthy T=2 pilot with `series-jz-v2` metrics and metadata.
- `nbody/analysis/presentations/conference_2026/m4_series/`: eight accepted
  safe series, corrected explicit `series_index.csv`, and `processing_report.md`;
  two large/pathological series are deferred and were not launched.
- `nbody/analysis/presentations/conference_2026/run_manifest.csv` and
  `run_manifest_metadata.json`: 11 manifest rows, 9 safe scans and 2 explicit
  deferred rows; no large deferred log was scanned.
- `nbody/analysis/presentations/conference_2026/campaign_metrics.csv` and
  `campaign_metrics_metadata.json`: 11 summary rows, 9 `ok` and 2 `missing`,
  fixed T2/T5 windows, no interpolation or implicit fallback.
- `nbody/analysis/presentations/conference_2026/claims.csv` and `reproduce.md`:
  four conservative claims, explicit source locators, and a reproducible figure
  command; the two deferred runs remain missing evidence.
- `nbody/analysis/presentations/conference_2026/figs/`: four rendered PNGs and
  `figure_manifest.csv`; all four were inspected for readability/clipping, while
  the manifest remains `visual_review_pending=true` until final deck integration.
- `nbody/scripts/analysis/runners/make_conference_figures.py`: explicit-CSV
  runner, no glob/fallback/HDF5/log reads; py_compile, --help, runner, and full
  pytest passed.
- `nbody/scripts/conference/manifest.py`, `tests/test_conference_manifest.py`:
  M1 schema/CLI/parser tests and actual 11-run scan evidence as summarized
  above; final package regeneration is pending M4.
- Jz/frame branch: 28 targeted tests passed; known intentional rotation-frame
  migration remains visible for integration review.
- Dissipation branch: 20 tests passed; deterministic 15-row validation CSV,
  source-audit hashes, and explicit `not_validated_in_solver` limitation.

Decisions: choice, reason, evidence
- Keep `agent/dev` and preserve the three untracked plan files: required by the
  campaign and observed in the initial status.
- Enforce sequential low-reasoning delegation: one `gpt-5.6-luna` subagent,
  root acceptance, then the next bounded task. This is a current user override
  of any earlier parallel/max-reasoning delegation wording.
- Use one local stage-checkpoint commit after each accepted M-stage; stage only
  explicit paths, record SHA/scope/tests here, then push only to a confirmed
  remote/ref and record the factual result. The current M7 push is pending the
  safety confirmation of `origin/agent/dev`.
- Do not start any simulation or solver validation: explicitly outside current
  permissions; no matching process was running.
- Keep pathological runs in the manifest with independent status/health and
  diagnostic flags; do not discard them or downgrade the evidence to failed.
- Conference package permissions were corrected with `g+rwX`; the canonical
  manifest was regenerated after M4 integration and accepted in M6.
- PNG visual review is available through built-in `view_image`; all four new
  M7 figures were inspected, but final deck-level visual freeze remains open.
- Treat disk space as a pre-run gate: 37 GiB free / 84% used at preflight.
- Do not launch `dsidm_s2p5_D0p75_N1e5_T2` or
  `dsidm10_f01_k0_N1e5_T5` without a fresh resource/pathology check and an
  explicit bounded task; their deferral is recorded in `m4_series/`.

Pending questions: ID, requested choice, channel, dependent tasks
- Q-M0-01: provide conference date (current session); dependent on final
  calendar timing only, not on M1–M3.

Next actions: 1..3 concrete steps
1. Create/update the editable slide source so the four accepted figures and
   claim IDs have explicit locators; keep `science_partial` and deferred rows.
2. Export the slide source (or record `export_blocked`), inspect the rendered
   output, and reconcile notes/Q&A with the final claims and limitations.
3. Prepare M8 handoff/rehearsal checklist and, after remote/ref confirmation,
   push the local stage commits; treat deferred logs as a separate resource
   decision, not an automatic launch.

Checkpoint commits (push status must be recorded separately):
- `5503e8e` — M0 plan/backlog/state documents; full pytest passed.
- `10b554c` — M1 manifest module/tests; full pytest passed.
- `49cbb17` — M2–M4 Jz/streaming/summary code/tests; full pytest passed.
- `d8934a3` — M3 dissipation audit/validation/tests; full pytest passed.
- `d161e84` — accepted M4 pilot/safe-series artifacts; full pytest passed.
- `be092e3` — accepted M6 manifest/index/campaign summary; full pytest passed.
- `b76500e` — M7 talk outline/notes/Q&A drafts; full pytest passed.
- `5924b52` — M7 figures, claims, reproducibility runner and manifest; full
  pytest passed; `push_pending` for `origin/agent/dev` because the safety gate
  rejected the unverified destination (no successful push output).

Resume: what to inspect before any new launch
- Read this file; verify branch/HEAD, permissions, live processes, target run
  and IC paths, and the exact approval before any heavy operation. Delegate at
  most one bounded task to `gpt-5.6-luna` (`low`), wait, independently inspect
  and accept/reject it, then continue. Local stage commits are authorized by
  the current user request; do not infer approval for new simulations, solver
  validation, Telegram, or push from this state file.
