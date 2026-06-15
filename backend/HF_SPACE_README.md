---
title: NeuroPulse Backend
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# NeuroPulse Backend

FastAPI service powering [NeuroPulse](https://github.com/84yk8btb9f-prog/neurolens) — open-source brain-response analysis for marketing content.

## Endpoints

- `POST /analyze` — score image / video / YouTube URL / PDF / text across 8 brain regions
- `POST /compare` — A/B compare two pieces of content
- `GET /personas` / `POST /personas` / `PUT /personas/{id}` / `DELETE /personas/{id}` — manage Creator Personas
- `GET /projects` / `POST /projects` / `GET /projects/{id}` / `DELETE /projects/{id}` — saved analyses
- `POST /projects/{id}/share` / `GET /share/{token}` — public read-only share links
- `GET /health` · `GET /model/status` · `POST /model/unload` · `GET /whisper/status`

## Stack

- Python 3.11 + FastAPI + Uvicorn
- CLIP ViT-L/14 (HuggingFace transformers) for brain region scoring
- Whisper base (CPU) for video transcription
- yt-dlp for video URL downloads
- SQLite for project + persona storage

## Environment

| Var | Purpose |
|---|---|
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins (e.g. `https://neurolens.vercel.app`) |
| `HF_TOKEN` | HF read/write token — required for the persona generator (LLM extraction via Inference API). Get one at https://huggingface.co/settings/tokens |

## Deploy your own

This Space is deployed as a Docker container. The `Dockerfile` installs ffmpeg, Python deps, and runs uvicorn on port 7860.
