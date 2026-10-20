# Workflow: inspect the plot registry (read-only)

Use for catalog questions, checking whether a plot exists, or identifying the registered runner/config for a request. Do not run plot runners in this workflow.

1. Read `nbody/analysis/REGISTRY.md` (container path `/nbody/analysis/REGISTRY.md`). It is generated and is the only maintained catalog.
2. Filter by block, meaning, data source, or input type. Summarize relevant plot names, what they show, runner, and expected output filename. Do not dump the whole registry unless asked.
3. If the file is missing or clearly stale for the requested block, print the live registry without rewriting it:

   ```bash
   docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/registry_docs.py --print
   ```

   When the container is unavailable, use the documented read-only local equivalent from `nbody/scripts/analysis/runners/registry_docs.py` with `NBODY_ANALYSIS_ROOT=/tmp/nbody-analysis`.

4. If the user asks which plot best answers a scientific question, explain the candidate(s) and their inputs; do not render them unless asked. Avoid claims that go beyond the registered summary or available evidence.

Read-only means no runner invocation, no registry regeneration without `--print`, and no file edits.
