# NeuroPulse

![License: MIT](https://img.shields.io/badge/license-MIT-F3F2EE?style=flat-square&labelColor=0B0B0D)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-F3F2EE?style=flat-square&labelColor=0B0B0D)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20Next.js-F3F2EE?style=flat-square&labelColor=0B0B0D)

Drop in any ad — video, image, or copy. See how the brain reacts before you spend a dollar promoting it.

NeuroPulse is an open-source brain-response analysis tool for marketing content. It scores creative across 8 brain regions, gives you actionable recommendations, and lets you analyze content through the lens of well-known direct-response creators.

CPU-only. No GPU. Free and open source — self-host to keep local-file and text scoring on your server. Model downloads, URL inputs, and optional persona generation contact external services.

## Quick start (local)

Requires: Python 3.11+, Node.js 20.9+, ffmpeg (`brew install ffmpeg`).

```bash
git clone https://github.com/nikolas-sapa/neurolens
cd neurolens
bash start.sh
```

Open http://localhost:3000. First run downloads ~600 MB of model weights (cached after that).

## What it does

- Score any image, video, supported YouTube/TikTok/Instagram video URL, PDF, or text across 8 brain regions
- Get a single-line verdict that tells you the weakest spot up front (e.g. *"Forgettable — this won't stick in memory five minutes after viewing"*)
- See per-region breakdowns and concrete recommendations
- Compare two pieces of content side-by-side
- Apply Creator Personas (Hormozi, GaryVee, Brunson, Yadegari, or your own) to layer creator-style tactical steps onto recommendations
- **Generate personas from content** — paste book excerpts, transcripts, tweet threads, or NotebookLM exports and have an LLM extract the creator's tactical playbook into the 8 brain-region structure
- Save analyses as named projects, share read-only links

Remote inputs accept HTTPS links to individual YouTube videos, TikTok video pages, and Instagram posts/reels. Playlist, channel, redirect and unrelated URLs are rejected. Short TikTok redirect links can be uploaded as local video files instead.

## What it isn't

- Not a peer-reviewed neuroscience instrument. Scores are derived from CLIP ViT-L/14 cosine similarity against neuroscience-informed probe texts. Treat the output as a creative review heuristic, not a clinical signal.
- Not a substitute for real performance data. If you have ROAS / CTR / conversion data, use it.
- No multi-user auth or billing — open source, run it yourself.

## What is NeuroPulse

**NeuroPulse is an open-source ad creative analysis tool that scores any image, video, or copy across 8 brain regions and tells you the single weakest spot before you spend money promoting it.** It runs on CPU, needs no GPU, and self-hosts so you control local analysis data.

### Why NeuroPulse

Most creative feedback is vague — "make it punchier," "the hook is weak." NeuroPulse gives you a specific verdict tied to a specific region: *"Forgettable — this won't stick in memory five minutes after viewing"* points you at the Hippocampus (memorability) score, not a hand-wave. You get per-region breakdowns and concrete recommendations you can act on in the next edit.

### NeuroPulse vs. the alternatives

| | NeuroPulse | Neuromarketing SaaS (Neurons, Realeyes) | Human focus groups | Just running the ad |
|---|---|---|---|---|
| Cost | Free, open source | Paid subscription, per-seat | Expensive per session | Ad spend + time |
| Setup | Self-host or hosted demo | Vendor account | Recruit panel | Live campaign |
| Speed | Seconds | Minutes to hours | Days | Days to a verdict |
| Privacy | Runs locally, no third-party calls | Data sent to vendor | N/A | Platform sees all |
| What you get | Per-region score + specific recommendation | Attention/emotion heatmaps | Qualitative opinions | Real ROAS/CTR |

Honest limits: NeuroPulse is a creative-review heuristic (CLIP cosine similarity against neuroscience-informed probe texts), **not** a peer-reviewed instrument and **not** a replacement for real performance data. If you already have ROAS/CTR, trust that first. NeuroPulse is for the stage before you spend.

### When to use NeuroPulse

- Pre-flight check on an ad before it goes live
- Comparing two creative variants and wanting a reason, not a coin flip
- Fast iteration on hooks, thumbnails, and opening frames
- Applying a specific creator's playbook (Hormozi, GaryVee, Brunson, or one you generate) to your own creative
- You want a self-hosted, private tool with no vendor and no per-seat cost

### FAQ

**Is NeuroPulse real neuroscience?**
No. Scores come from CLIP ViT-L/14 cosine similarity against neuroscience-informed probe texts, mapped to 0–100. Treat it as a structured creative-review heuristic, not a clinical or peer-reviewed signal.

**Does it need a GPU?**
No. CPU-only. First run downloads ~600 MB of model weights, cached after that.

**Can I run it fully private?**
Local-file and text scoring run on your server. Downloading model weights and analyzing remote URLs contact external services. The optional persona generator sends source text to Hugging Face; omit `HF_TOKEN` to keep that feature disabled.

**What can it analyze?**
Images, video, YouTube/TikTok/Instagram URLs, PDFs, and raw text. Whisper transcribes video audio so spoken copy feeds the language and persuasion regions.

**What's the persona generator?**
Paste book excerpts, transcripts, or tweet threads and an LLM extracts that creator's tactical playbook into the 8-region structure, then layers their steps onto your recommendations.

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

PRs welcome — keep them tight and tested. See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup for both the backend and frontend, repo layout, and PR expectations. This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).

```bash
# backend
cd backend && pytest tests/

# frontend
cd frontend && npx tsc --noEmit
```

## License

MIT — see [LICENSE](LICENSE).
