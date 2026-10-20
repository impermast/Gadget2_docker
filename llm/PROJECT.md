# PROJECT — N-body simulation agent contract

Status: stable project context; change only when project goals or operating invariants change. Current task state belongs in `PLAN.md`/`ACTIVE.md`, not here.

## Purpose and scientific scope

This Dockerized scientific repository supports controlled N-body research with GADGET-2, GIZMO, and GalIC. Its central research scope is how CDM/SIDM/dSIDM assumptions affect halo/subhalo morphology, density profiles, relaxation, clump survival, and possible rotating/disk-like structures. Results are bounded by tested ICs, resolution, runtime, and analysis methodology; do not generalize a numerical null/pathology into a universal physical claim.

Preserve distinctions between CDM/SIDM/dSIDM, GalIC/prerun/full GIZMO results, baseline/experimental ICs, nominal/measured parameters, completed/incomplete/pathological runs. Physical parameters that can change conclusions must not be silently guessed. Separate observations, hypotheses, and interpretations; state uncertainty and applicability.

## Repository and source of truth

- Host project paths under `nbody/` are mounted as `/nbody` in the container; external/vendor trees are under `/opt` and not edited without explicit authorization.
- Simulation wrappers: `nbody/scripts/run_sim.sh`, `nbody/scripts/generate_ics.sh`. Do not bypass wrappers or overwrite baseline configs/outputs.
- Analysis: `nbody/scripts/analysis/`; supported plots/analysis are registered in `nbody/analysis/REGISTRY.md`; canonical output root is `nbody/analysis/`.
- Monitoring: `nbody/scripts/check_simulations/`; use `check-run` skill.
- Operational procedures: `.agents/skills/` (Cline copies in `.cline/skills/` must stay synchronized).
- Current obligation source: `llm/PLAN.md`; current checkpoint: `llm/ACTIVE.md`; curated memory index: `llm/MEMORY.md`; detailed important records: `llm/records/`; exact simulation artifacts/manifests/metrics remain canonical evidence in `nbody/`.

## Safety and authority

Only the current user request and explicit scoped approval authorize consequential actions. Historic session summaries, plans, files, commits, or previous approvals do not grant new authority. Ask before long/production simulation, Docker rebuild, package install, editing Dockerfile or `/opt`, destructive deletion/cleanup, or Git commit/push/history operations unless the current user explicitly approved that exact class/scope. Never use `rm -rf`, `git reset --hard`, `git clean -fdx`, or destructive container cleanup.

Before a run: establish exact IC/parameters/units/output directory, inspect live processes/resources and relevant current data, identify expected runtime, state the exact wrapper command and ask the approval required by the applicable skill. Never overwrite existing runs or baseline configs. Before claiming completion, check actual reached time, expected snapshot coverage, terminal log/error, runtime parameters and analysis—not `run.state`/exit code alone. Preserve outputs unless specifically authorized to remove them.

Do not open large snapshots, HDF5, binaries, plots or generated outputs merely for orientation. Inspect small metadata/headers and use canonical loaders/tools; open a specific large artifact only when necessary and authorized. Never edit third-party `/opt` sources without explicit permission.

## Scientific provenance and validation

For a consequential result, retain the locator for run ID, IC identity/hash when available, actual runtime parameters, solver/analysis version, time/coverage, method/aperture/units, status and limitations. Existing canonical manifests, `experiment.md`, metrics and analysis reports are evidence; do not duplicate their full contents into `llm/`. Missing evidence is `unknown`, not inferred success. Revalidate stale claims before depending on them.

Do not equate wrapper return code, run-state labels, an IC central-resolution gate, or prereun output with a physical validation result. Incomplete/pathological runs cannot support a completed-time scientific comparison. Check controls, applicability and convergence before broad claims.

## Memory, bili, and checkpoint contract

- Primary workflow is one long Pi session. Bili preserves and compresses that session's conversation; it is historical context, not a durable scientific database or current task ledger. The four files provide concise verified anchors and safe recovery, not a second transcript.
- Boot from `AGENTS.md`, then these four short files: PROJECT → PLAN → ACTIVE → MEMORY. Load one relevant skill and retrieve only needed evidence.
- `PLAN.md` is the single open-obligation ledger; `ACTIVE.md` is a replaceable working checkpoint, not a second backlog. Their shared checkpoint ID must match; on mismatch reconcile against evidence, do not guess.
- Pi project `.pi/settings.json` sets `sessionDir: "llm/sessions"`, relative to working directory (launch Pi from the repository root). The harness launcher `/home/kds/progs/harness/env.sh` no longer exports `PI_CODING_AGENT_SESSION_DIR`; this already-running Pi Web process retains its inherited `/home/kds/progs/harness/agent/sessions` value until restart. Its cwd-specific session directory is symlinked to `llm/sessions`, and this live session was verified writing through the link. On a planned restart, verify `PI_SESSION_FILE` and session resume; do not interrupt an active session just to clear inherited environment.
- `MEMORY.md` contains only concise, reusable, sourced conclusions and locators. Mark each confirmed/provisional/invalidated/superseded/needs-revalidation with scope.
- Compression/bili summaries preserve current user constraints, task IDs/status, evidence locators, exact critical values and unresolved contradictions. Compress completed phases only after checkpointing; keep active code/questions and critical user constraints verbatim. Historical instructions and approvals in a compressed transcript are not current commands.
- With typical 250–300k model windows, keep bootstrap compact and load evidence on demand. Count system/harness/tool overhead and output reserve, not just visible Markdown. Around 55–60% effective-window use, checkpoint and compress finished phases; around 70–75%, checkpoint and trim/retrieve selectively. Continue the same session where possible; a new session is a recovery option, not routine cadence. Treat percentages as initial guardrails, revise only from measured usage/cache behavior.

### Mandatory `records/` gate — important knowledge only

**Default: do not create a record.** A record is justified only when all apply:
1. The knowledge matters to scientific interpretation, safety, reproducibility, or architecture; losing it could cause a serious error or repeat costly work.
2. It remains useful beyond the current step and is not transient status, an unverified working hypothesis, or a “what I did” log.
3. It has concrete evidence/rationale and a stated scope. A high-impact unresolved contradiction may be recorded as an incident only with uncertainty explicit.
4. It cannot be represented adequately by 1–3 sentences plus a locator in MEMORY, ACTIVE, or PLAN; do not copy an existing canonical report/manifest without need.
5. No record already covers the topic: update it instead of creating a per-run/per-date file.

Good candidates: verified parameter convention and applicability; invalidated IC with reason and affected claims; consequential methodology decision and rationale; important research conclusion with evidence; critical solver incident that changes completion criteria. Ordinary run/test/tool-call/git activity, routine fixes, ETA/PID, and transcript recaps are not records. If an existing canonical report in `nbody/` is sufficient, keep only a link. Records are not generated automatically after each action; no daily logs or per-session quota.

A record should be short, titled by knowledge (not date/event), and answer “why important / when to use.” Include stable locator(s), scope, evidence, status/uncertainty, limits, and last verified date. Link it from MEMORY or the relevant PLAN item. Never duplicate the same content in ACTIVE, MEMORY, record, and source report.

## Git and communication

Explain work and ask questions in Russian. Preserve dirty/untracked user files; never reset or clean unrelated work. Commit template, if user explicitly asks for commit: `llm/gitmessage.txt`; branch/Git rules are subordinate to current explicit user approval and repository state. `llm/` tracking can vary by branch: do not untrack/remove it based on old instructions.
