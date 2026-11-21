# SecretShield

Find leaked passwords and keys in Git repositories, including old history.

> Work in progress. See [docs/DESIGN.md](docs/DESIGN.md) for the full plan.

## Setup

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
