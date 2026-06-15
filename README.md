# NeuroPulse

Drop in any ad — video, image, or copy. See how the brain reacts before you spend a dollar promoting it.

NeuroPulse is an open-source brain-response analysis tool for marketing content. It scores creative across 8 brain regions, gives you actionable recommendations, and lets you analyze content through the lens of well-known direct-response creators.

**Live demo:** <https://neurolens-nine.vercel.app/>
**Backend API:** <https://niksapa-neurolens-backend.hf.space/health>

CPU-only. No GPU. Free and open source — use the hosted demo above, or self-host for full privacy (no third-party calls).

## What it does

- Score any image, video, YouTube/TikTok/Instagram URL, PDF, or text across 8 brain regions
- Get a single-line verdict that tells you the weakest spot up front (e.g. *"Forgettable — this won't stick in memory five minutes after viewing"*)
- See per-region breakdowns and concrete recommendations
- Compare two pieces of content side-by-side
- Apply Creator Personas (Hormozi, GaryVee, Brunson, Yadegari, or your own) to layer creator-style tactical steps onto recommendations
- **Generate personas from content** — paste book excerpts, transcripts, tweet threads, or NotebookLM exports and have an LLM extract the creator's tactical playbook into the 8 brain-region structure
- Save analyses as named projects, share read-only links

## What it isn't

- Not a peer-reviewed neuroscience instrument. Scores are derived from CLIP ViT-B/32 cosine similarity against neuroscience-informed probe texts. Treat the output as a creative review heuristic, not a clinical signal.
- Not a substitute for real performance data. If you have ROAS / CTR / conversion data, use it.
- No multi-user auth or billing — open source, run it yourself.

## Quick start (local)

Requires: Python 3.11+, Node.js 18+, ffmpeg (`brew install ffmpeg`).

```bash
git clone https://github.com/84yk8btb9f-prog/neurolens
cd neurolens
bash start.sh
```

Open http://localhost:3000. First run downloads ~600 MB of model weights (cached after that).

## Deploy your own

The backend runs as a Docker container; the frontend is a standard Next.js app. Free hosting works:

### Backend → Hugging Face Space (free, 16 GB RAM)

1. Create a new Space at <https://huggingface.co/new-space> — pick **Docker** as the SDK
2. Clone your new Space locally: `git clone https://huggingface.co/spaces/<you>/neurolens-backend`
3. Copy `backend/Dockerfile`, `backend/requirements.txt`, `backend/app/`, and `backend/HF_SPACE_README.md` (rename to `README.md`) into the Space repo
4. In the Space settings, add environment variables:
   - `ALLOWED_ORIGINS` = `https://your-frontend.vercel.app`
   - `HF_TOKEN` = a HF write token (only needed for the persona generator) — <https://huggingface.co/settings/tokens>
5. Push to the Space — it will build and start. First request triggers a CLIP weight download (~600 MB for ViT-L/14).

### Frontend → Vercel (free)

1. Push this repo to GitHub
2. Import the repo at <https://vercel.com/new>, set the root directory to `frontend`
3. Add an environment variable:
   - `NEXT_PUBLIC_API_URL` = your HF Space URL (e.g. `https://<you>-neurolens-backend.hf.space`)
4. Deploy. Done.

## Updating the deployment

```bash
# Backend changes → push to HF Space (one command)
bash scripts/deploy-hf.sh

# Frontend changes → just push to GitHub, Vercel auto-deploys
git push
```

The HF deploy script syncs `backend/` into your local Space clone at `/tmp/np-space`, commits, and pushes. Set `HF_SPACE_DIR` if you want a different path.

## How it works

CLIP ViT-L/14 encodes content (images and text) into shared semantic embeddings. Each brain region has 3-4 probe texts describing what activates it; cosine similarity to the best-matching probe gets linearly mapped from a calibrated reference range to 0-100. Whisper transcribes video audio so spoken content also feeds the language/persuasion regions.

Per-region probes live in `backend/app/clip_scorer.py` and are easy to tune. Personas are stored in SQLite and editable from the `/personas` page.

| Region | What it captures |
|---|---|
| Visual Cortex | Whether the visual hook pulls attention |
| Face & Social | Human presence and trust signal |
| Amygdala | Emotional charge |
| Hippocampus | Memorability and narrative arc |
| Language Areas | Copy clarity and voice |
| Reward Circuit | Payoff signal — what's in it for them |
| Prefrontal Cortex | Logical proof and reasons to believe |
| Motor Action | Strength of the call to action |

## Stack

- **Backend:** Python 3.11 · FastAPI · CLIP ViT-L/14 (HF transformers) · Whisper base · yt-dlp · SQLite
- **Frontend:** Next.js App Router · shadcn/ui · Recharts · Tailwind
- **Storage:** Local SQLite (no Postgres, no cloud)

## Project structure

```
backend/
  Dockerfile               HF Space deployment
  requirements.txt
  HF_SPACE_README.md       Front-matter for HF Space repo
  app/
    main.py                FastAPI routes
    content_processor.py   Routes uploads to the right processor
    clip_scorer.py         CLIP probe-text scoring
    brain_mapper.py        Public scoring surface
    model_manager.py       Load/unload + idle watchdog
    headline.py            One-line verdict generator
    recommendation_engine.py
    personas.py            Persona application
    persona_storage.py     SQLite CRUD for personas
    storage.py             SQLite CRUD for projects + share tokens
    processors/            Per-format processors (image, video, pdf, youtube, text)
    whisper_manager.py
  tests/                   Pytest suite (124 tests)

frontend/
  src/
    app/                   Next.js routes (/, /analysis, /compare, /projects, /personas, /share/[token])
    components/            BrainRadarChart, RegionCard, RecommendationPanel, Headline, ShareButton, PersonaSelector, …
    lib/api.ts             Backend client
    types/analysis.ts
  .env.example             NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Contributing

Side project / portfolio piece. PRs welcome — keep them tight and tested.

```bash
# backend
cd backend && pytest tests/

# frontend
cd frontend && npx tsc --noEmit
```

## License

MIT.
