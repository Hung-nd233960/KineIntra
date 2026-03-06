# Appendix A: Setup

- Environment:
  - OS: Linux (verified), cross-platform notes.
  - Dependencies: see `requirements.txt`, `pyproject.toml`.
- Building & running:

```bash
# List ports and connect
python -m kineintra.cli ports
python -m kineintra.cli connect --port virtual --monitor
```

- GUI prerequisites: PyQt6 installed.
- TCP mode: ensure remote server/adapter availability.
