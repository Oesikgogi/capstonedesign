# Boo키우기 API

FastAPI backend for the Boo키우기 app.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Seed Data

```bash
python -m app.seed_quizzes
python -m app.seed_school_foods
```

## ERD

See [docs/ERD.md](docs/ERD.md).
