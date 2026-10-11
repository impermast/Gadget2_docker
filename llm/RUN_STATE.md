# RUN_STATE

Updated UTC: 2026-10-11

Campaign ID / spec revision:
- `conference_2026_dsidm`
- `llm/CODEX_AUTONOMOUS_PROMPT.md` sha256 `5388c732b45d2b59984b338f32c5bc04932da0c94949042d5e6cb61a4b0bac98`
- `llm/CONFERENCE_TWO_WEEK_PLAN.md` sha256 `85497dcbdba0cf7898d974e03143f3d7d2500cf69caf710960fa80260dd2acfa`
- `llm/implementation_plan.md` sha256 `3658ffdc11843aca82028f671b8cb196e285caf2312a1f9d7f284f717cf5e2e2`

Orchestration policy (current user override):
- At most one live subagent at a time.
- Delegate substantive bounded tasks to `gpt-5.6-luna` with reduced
  reasoning effort (`low`); wait for completion before issuing another task.
- The root agent independently checks and accepts or rejects every result
  before continuing. A rejected result is returned to the same agent for a
  bounded correction; no parallel delegation is allowed.

Branch / HEAD / initial dirty paths / owned changes:
- Branch: `agent/dev`; HEAD: `0c4b6075be0f1de29c4cc8c4f04edeaacf3e42cb`.
- Initial dirty paths: `llm/CODEX_AUTONOMOUS_PROMPT.md`,
  `llm/CONFERENCE_TWO_WEEK_PLAN.md`, `llm/implementation_plan.md` — user-owned
  untracked plan files intentionally edited in the previous user request as
  the base for multi-day work before campaign start; preserve them unchanged.
- State sync after M1–M3 verification: manifest/Jz/dissipation branches are
  recorded below; this file remains the only state file changed in this sync.

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
  validation, no sigma/m=5 runs, no Telegram/external messages, no commit and
  no push. The canonical manifest is regenerated only after M4 integration.
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
  canonical manifest output remains intentionally pending final M4 regeneration.
- Resources at check: 16 online CPUs; load 1.54/0.68/0.41; RAM 14 GiB total,
  10 GiB available; swap 1.9 GiB with 768 KiB used; workspace filesystem
  232 GiB total, 183 GiB used, 37 GiB available (84%), inode use 12%.
- Rendering/export: `pdftoppm` and `pdfinfo` available for PDF inspection,
  `libreoffice`/`soffice` available for office/slide conversion, `xdg-open`
  available; built-in `view_image` successfully confirmed PNG visual review
  on an existing figure. Dedicated `feh`/`eog`/ImageMagick, `pandoc`, `marp`,
  `quarto`, browser exporters, `pypdf`, and `python-pptx` were not found;
  dedicated binaries are not needed for PNG review. PDF/slide export remains
  a later check. Rendering of new figures is still pending. Background
  execution/waiting primitives `nohup`, `setsid`, and `timeout` are present;
  a shell background/wait smoke check passed in 0.103 s.

Milestones: M0..M8 -> pending | in_progress | done | blocked | deferred
- M0 `done` — preflight, baseline, permissions, and initial state recorded.
- M1 `done` — manifest code/tests verified; 11 old runs inventoried (10
  completed, 1 incomplete; 9 healthy, 2 pathological; metrics 6 complete,
  1 partial, 4 missing). Canonical artifact awaits final post-M4 regeneration.
- M2 `done` — Jz/mass/frame implementation and 28 targeted tests verified;
  intentional rotation-frame migration is documented by the delegated branch.
- M3 `done` — 20 tests and deterministic 15-row validation CSV verified;
  source audit hashes recorded; solver experiment remains not validated.
- M4 `in_progress` — bounded-memory sync scan/metadata and explicit late-time
  summarizer branches are integrated and tested. A pilot plus eight safe
  existing series produced 313 metric rows in `m4_pilot/` and `m4_series/`;
  two large/pathological logs remain explicitly deferred by the resource gate.
- M5 `pending`; M6 `pending`; M7 `pending`; M8 `pending`.

Current task / acceptance check:
- M0–M3 acceptance evidence is recorded above. M4 code and scoped/full tests
  passed; the pilot and eight safe real-series runs were independently checked
  by the root agent. Current task: build the campaign summary from the explicit
  index, then decide whether the deferred logs can be processed under a new
  resource gate. No new simulation or solver validation is implied.

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
- `nbody/analysis/presentations/conference_2026/m4_series/`: explicit
  `series_index.csv`, eight accepted safe series, and `processing_report.md`;
  two large/pathological series are deferred and were not launched.
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
- Do not start any simulation or solver validation: explicitly outside current
  permissions; no matching process was running.
- Keep pathological runs in the manifest with independent status/health and
  diagnostic flags; do not discard them or downgrade the evidence to failed.
- Conference package permissions were corrected with `g+rwX`; defer canonical
  manifest regeneration until M4 integration so it reflects the final schema.
- PNG visual review is available through built-in `view_image` and was
  confirmed on an existing figure; keep review of newly rendered figures as a
  required M6–M7 action. PDF/slide export is a separate later check.
- Treat disk space as a pre-run gate: 37 GiB free / 84% used at preflight.
- Do not launch `dsidm_s2p5_D0p75_N1e5_T2` or
  `dsidm10_f01_k0_N1e5_T5` without a fresh resource/pathology check and an
  explicit bounded task; their deferral is recorded in `m4_series/`.

Pending questions: ID, requested choice, channel, dependent tasks
- Q-M0-01: provide conference date (current session); dependent on final
  calendar timing only, not on M1–M3.

Next actions: 1..3 concrete steps
1. Build `campaign_metrics.csv`/metadata from the explicit `m4_series` index;
   keep partial/deferred status visible and avoid implicit globbing.
2. Regenerate and independently verify the canonical manifest only after the
   final series mapping is integrated.
3. Prepare figures/claims and export checks; treat the deferred logs as a
   separate approval/resource decision, not an automatic launch.

Resume: what to inspect before any new launch
- Read this file; verify branch/HEAD, permissions, live processes, target run
  and IC paths, and the exact approval before any heavy operation. Delegate at
  most one bounded task to `gpt-5.6-luna` (`low`), wait, independently inspect
  and accept/reject it, then continue. Do not infer approval for new
  simulations, solver validation, Telegram, commit, or push from this state
  file.
