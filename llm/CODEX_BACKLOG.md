# M0 backlog

| Severity | Locator | Symptom / reproduction | Impact | Status |
|---|---|---|---|---|
| medium | M0 rendering capability | At M0, `feh`, `eog`, `display`, ImageMagick, `pypdf`, `python-pptx`, and slide/browser exporters were absent. Current `/usr/bin/python3` provides `python-pptx`; `export_slides.py` builds a structurally checked PPTX, while LibreOffice PDF conversion still exits non-zero in the headless runtime. | PNG review is available, PPTX structure is checked, but PDF export and deck-level visual review remain unverified; do not claim visual review until a usable PDF route is confirmed | partial |
| medium | workspace filesystem (`df -h /home/kds/sci/gadget2_docker`) | 232 GiB total, 183 GiB used, 37 GiB available, 84% used at M0 | resource headroom must be recalculated before any heavy run or generated-data block | monitor |
## Rendering capability

- Resolved: PNG visual review is available and confirmed through built-in
  `view_image`; dedicated viewer binaries are not required for PNG.
- Resolved partially: `/usr/bin/python3` plus `talk/export_slides.py` produces a
  16-slide PPTX with four embedded figures and preserved status badges.
- Remaining: run LibreOffice in a writable user runtime, verify PDF with
  `pdfinfo`/`pdftoppm`, and visually review the deck; badges remain pending.
