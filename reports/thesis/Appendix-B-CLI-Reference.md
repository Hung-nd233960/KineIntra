# Appendix B: CLI Reference

- CLI doc: [docs/CLI.md](docs/CLI.md)
- Common commands:

```bash
python -m kineintra.cli ports
python -m kineintra.cli connect --port virtual --monitor
python -m kineintra.cli status --seq 1
python -m kineintra.cli set-nsensors 8
python -m kineintra.cli set-rate 0 100
python -m kineintra.cli set-bits 0 12
python -m kineintra.cli set-active 0x3
```

- TCP mode:

```bash
python -m kineintra.cli connect --tcp-host 127.0.0.1 --tcp-port 8888 --monitor
```
