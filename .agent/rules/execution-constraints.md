---
trigger: always_on
---

# Rule 2: Execution Constraints

- Work only inside this workspace; do not touch sibling projects under `E:\Own-Projects`.
- Modify only requested files; no unrelated refactors; add only needed imports.
- Do not copy code from third-party repos into this project without confirming its licence first.
- Never commit, push, or run destructive commands without explicit approval.
- Keep replies concise; do not paste whole files or repeat unchanged code.
- Excluded from scans: `node_modules/`, `dist/`, `.venv/`, `__pycache__/`, `.git/`, `*.db`.
