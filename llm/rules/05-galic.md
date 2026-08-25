# GalIC workflow rules

GalIC is used to generate galaxy initial conditions.

Rules:

- Keep GalIC source/binary under `/opt/GalIC`.
- Keep user parameter files and generated ICs under `nbody/GalIC/`.
- Do not edit `/opt/GalIC` unless explicitly requested.
- For new initial conditions:
  - copy an existing param file;
  - modify particle number, mass model, halo/disk/bulge parameters as requested;
  - write output to a new named file;
  - record the generated IC path in `llm/memory-bank/experimentLog.md`.
- Do not generate large ICs without explicit confirmation.
- The canonical param template is: `nbody/GalIC/halo_nfw_ics.param`.
- After generating ICs, `generate_ics.sh` converts PartType1 → PartType3 using `nbody/scripts/convert_to_pt3.py` for SIDM compatibility.