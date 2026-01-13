# System Diagrams

This folder contains UML and architectural diagrams for the KineIntra / Communication Stack system.

## Contents

| File | Description |
|------|-------------|
| [01-BlockDiagram.md](01-BlockDiagram.md) | High-level system block diagram |
| [02-UseCaseDiagram.md](02-UseCaseDiagram.md) | Actor and use case relationships |
| [03-Flowcharts.md](03-Flowcharts.md) | Control flow diagrams (MCU, Host, CLI) |
| [04-SequenceDiagrams.md](04-SequenceDiagrams.md) | Message sequence diagrams |
| [05-StateDiagram.md](05-StateDiagram.md) | Device state machine |
| [06-ClassDiagram.md](06-ClassDiagram.md) | Host software class structure |

## Rendering

All diagrams use [Mermaid](https://mermaid.js.org/) syntax. They render automatically on GitHub, GitLab, and in VS Code with the Mermaid extension.

To preview locally:

```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Render to PNG
mmdc -i 01-BlockDiagram.md -o block-diagram.png
```
