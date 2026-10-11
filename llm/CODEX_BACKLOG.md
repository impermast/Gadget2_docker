# M0 backlog

| Severity | Locator | Symptom / reproduction | Impact | Status |
|---|---|---|---|---|
| medium | M0 rendering capability | `feh`, `eog`, `display`, ImageMagick, `pypdf`, `python-pptx`, and slide/browser exporters were absent; `xdg-open`, `pdftoppm`, `pdfinfo`, LibreOffice, matplotlib, and PIL were present | PNG visual review and some export paths remain unverified; do not claim visual review until a usable route is confirmed | open |
| medium | workspace filesystem (`df -h /home/kds/sci/gadget2_docker`) | 232 GiB total, 183 GiB used, 37 GiB available, 84% used at M0 | resource headroom must be recalculated before any heavy run or generated-data block | monitor |
## Rendering capability

- Resolved: PNG visual review is available and confirmed through built-in
  `view_image`; dedicated viewer binaries are not required for PNG.
- Remaining: verify PDF/slide export later; newly rendered figures still need
  visual review.
