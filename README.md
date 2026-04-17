# Smart Traffic Control Agent (College Project)

This project implements a simple traffic control "agent" (`TrafficAgent`) with a browser-based simulator UI.

What I added:
- `requirements.txt` — minimal Python deps
- `.gitignore` — common ignores
- `tests/test_agent.py` — unit tests for core agent logic

Run locally:

1. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the app

```bash
set FLASK_APP=app.py
set FLASK_ENV=development
python app.py
```

3. Run tests

```bash
pytest -q
```

Next recommended improvements:
- Refactor into package (app factory)
- Add persistent telemetry (SQLite)
- Add CI (GitHub Actions) and linting (ruff/black)
- Add more unit tests for decision edge-cases
