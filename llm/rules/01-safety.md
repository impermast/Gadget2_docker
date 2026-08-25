# Safety rules

## Always require explicit user approval

- Long simulations.
- Docker image rebuilds.
- Package installation.
- Editing Dockerfile.
- Editing external/vendor source trees.
- Deleting files or directories.
- Changing Git history.
- Committing or pushing to `master`.
- Pushing without notifying the user (pushing the `agent/dev` branch IS allowed
  after informing the user; pushing directly to `master` is forbidden).
- Opening large binary/scientific data files.

## Never auto-run

- `rm -rf`
- `git reset --hard`
- `git clean -fdx`
- `docker system prune`
- `docker rm -f`
- `docker rmi`
- `git push` to `master` or with force flags
  (pushing the `agent/*` branch is allowed after notifying the user)

## Allowed after user asks for a simulation task

The agent may prepare and run a controlled simulation only if:

- the user explicitly asked to run a simulation;
- the affected parameter/config files are identified;
- the output directory is unique and not overwriting previous results;
- the command is shown before execution;
- the expected runtime class is stated:
  - quick test;
  - medium local run;
  - long production run.

For long production runs, ask for explicit confirmation before starting.