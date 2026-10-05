# Contributing to NeuroPulse

Thanks for taking a look. This is a small open-source project — PRs welcome, keep them tight and tested.

## Repo layout

```
backend/    FastAPI service (Python 3.11)
frontend/   Next.js App Router (Node.js 18+)
scripts/    Deploy helpers (e.g. scripts/deploy-hf.sh)
docs/       Project docs
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- ffmpeg (`brew install ffmpeg` on macOS)

## Run everything locally

```bash
git clone https://github.com/nikolas-sapa/neurolens
cd neurolens
bash start.sh
```

This starts the backend on `http://localhost:8000` and the frontend on `http://localhost:3000`. First run downloads the CLIP ViT-L/14 weights (~600 MB), cached after that — no GPU required.

## Backend only

```bash
cd backend
bash start.sh          # creates .venv, installs requirements.txt, runs uvicorn --reload on :8000
```

Manual equivalent:

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Run the test suite (124 tests):

```bash
cd backend && pytest tests/
```

Per-region CLIP probe texts live in `backend/app/clip_scorer.py` — that's the file to touch if you're tuning scoring.

## Frontend only

```bash
cd frontend
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

Type-check before opening a PR:

```bash
cd frontend && npx tsc --noEmit
```

Lint:

```bash
cd frontend && npm run lint
```

## Model weights

No manual download step — CLIP (ViT-L/14) and Whisper (base) weights are fetched automatically by `transformers`/`openai-whisper` on first backend request and cached locally. Nothing to check into the repo.

## Pull requests

- Keep PRs focused — one change per PR.
- Add or update tests for backend changes (`backend/tests/`).
- Run `pytest tests/` (backend) and `npx tsc --noEmit` (frontend) before opening.
- Describe what changed and why in the PR description; link any related issue.
- No unrelated formatting/dependency churn in the same PR as a functional change.

## Reporting bugs / requesting features

Use the issue templates under `.github/ISSUE_TEMPLATE/`. For security issues, see `SECURITY.md` instead of opening a public issue.

Default backend tests use local fixtures. Four real-model integration tests skip unless
you explicitly pass `pytest tests/ --run-models`. That option requires Torch/Transformers
and may download CLIP weights. URL and persona-generator tests mock external services;
no live inference credentials are required for default tests.
