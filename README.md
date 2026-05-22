# AdDigest — Advertising News Intelligence + Jonas AI Advisor

A two-feature internal AI system built with FastAPI, Gemini, ChromaDB and SQLite.

---

## Features

### 1 — News Intelligence + LinkedIn Article Generator
- Collects news from 8 top advertising/marketing sources via RSS (Adweek, AdAge, Digiday, MarketingWeek, CampaignLive, WARC, W&V, Horizont)
- Keyword-based relevance filtering and scoring
- AI summarization per article via Gemini
- Multi-article trend synthesis
- One-click LinkedIn article generation (professional, analytical, ready to publish)
- Source attribution and deduplication

### 2 — Jonas Bailly AI Advisor (RAG Chat)
- Internal strategic advisor in the style of Jonas Bailly (MD, Jung von Matt HAVEL)
- RAG: retrieves relevant persona notes before answering
- Full CRUD for persona knowledge base (notes, tags)
- Conversation memory within a session
- Clearly labelled as internal tool — not the real Jonas

---

## Quick Start

```bash
git clone <repo-url>
cd adnews-summarizer

# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
python -m nltk.downloader punkt punkt_tab averaged_perceptron_tagger

# 3. Configure environment
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY

# 4. Start the server
uvicorn main:app --reload --port 8000
```

Open the frontend: `web/index.html` in a browser (or via Live Server in VS Code).

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=models/text-embedding-004
DATABASE_URL=sqlite:///./news.db
CHROMA_DIR=./chroma_db
WEEK_LOOKBACK_DAYS=7
LOG_LEVEL=INFO
```

Get a Gemini API key at: https://aistudio.google.com/app/apikey

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check + Gemini status |
| `GET` | `/api/news` | Stored articles (limit param) |
| `POST` | `/api/scrape` | Trigger background scrape |
| `POST` | `/api/news/search` | Keyword search + summarize |
| `POST` | `/api/news/generate-linkedin-article` | Full pipeline → LinkedIn article |
| `GET` | `/api/persona/notes` | List persona notes (optional ?tag=) |
| `POST` | `/api/persona/notes` | Add note |
| `PUT` | `/api/persona/notes/:id` | Update note |
| `DELETE` | `/api/persona/notes/:id` | Delete note |
| `POST` | `/api/rag/reindex` | Re-embed all notes into ChromaDB |
| `POST` | `/api/chat` | Chat with Jonas AI advisor |

---

## Manual Test Scenarios

### 1 — Health check
```bash
curl http://127.0.0.1:8000/api/health
# Expected: {"status":"ok","gemini_configured":true,...}
```

### 2 — Keyword news search
```bash
curl -s -X POST http://127.0.0.1:8000/api/news/search \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["AI advertising", "programmatic"]}' | python3 -m json.tool
```

### 3 — Generate LinkedIn article
```bash
curl -s -X POST http://127.0.0.1:8000/api/news/generate-linkedin-article \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["brand strategy", "creative agencies"], "max_articles": 5}' \
  | python3 -m json.tool
```

### 4 — Add persona note
```bash
curl -s -X POST http://127.0.0.1:8000/api/persona/notes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Decision-making style",
    "content": "Jonas prefers to start from the client tension before jumping to solutions. He often asks: what is the real business problem here?",
    "tags": ["decisions", "style"]
  }' | python3 -m json.tool
```

### 5 — Chat with Jonas AI
```bash
curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "We have a pitch for a retail client next week. How should we frame the creative strategy?"}' \
  | python3 -m json.tool
```

### 6 — Re-index persona notes (after bulk edits)
```bash
curl -s -X POST http://127.0.0.1:8000/api/rag/reindex | python3 -m json.tool
```

---

## Project Structure

```
adnews-summarizer/
├── main.py                          ← FastAPI app + all routes
├── requirements.txt
├── .env.example
├── data/
│   └── persona_seed.json            ← Initial Jonas profile (auto-seeded on first run)
├── modules/
│   ├── ai/
│   │   ├── gemini_client.py         ← google-genai SDK wrapper
│   │   └── prompt_templates.py      ← All prompts in one place
│   ├── news/
│   │   ├── rss_collector.py         ← RSS fetch + keyword filter
│   │   ├── summarizer.py            ← Per-article + multi-article synthesis
│   │   └── linkedin_generator.py   ← LinkedIn article generation
│   ├── rag/
│   │   └── vector_store.py          ← ChromaDB + Gemini embeddings
│   ├── persona/
│   │   └── notes_service.py         ← CRUD + auto-indexing
│   ├── chat/
│   │   └── chat_service.py          ← RAG chat + conversation memory
│   └── storage/
│       ├── database.py
│       └── models.py
└── web/
    ├── index.html    ← News Intelligence page
    ├── chat.html     ← Jonas AI chat page
    ├── persona.html  ← Knowledge base manager
    └── style.css
```

---

## Migration Notes (from original)

- **Gemini API key**: was hardcoded as `"YOUR GEMNINI API KEY HERE"` → now read from `.env`
- **`google-generativeai` (deprecated)** → replaced with `google-genai` (v2+)
- **Single `main.py`** → split into `modules/` with separation of concerns
- **No Ollama**: was never actually used; reference removed
- **New features added**: keyword search, LinkedIn generator, RAG chat, persona CRUD, ChromaDB

---

## Deployment (VPS)

```bash
# Install
pip install -r requirements.txt
cp .env.example .env && nano .env  # set GEMINI_API_KEY

# systemd service — same as before, just update ExecStart:
ExecStart=/root/adnews-summarizer/venv/bin/gunicorn \
  -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000
```

Frontend served by Nginx from `/var/www/adnews/web/`.

---

## Limitations & Next Steps

- **RSS rate limits**: some feeds block frequent polling — add delays if needed
- **newspaper3k**: may fail on paywalled articles (graceful skip is in place)
- **ChromaDB**: local file-based — for multi-instance deploy, switch to a hosted vector DB
- **Conversation history**: stored in SQLite, not pruned automatically — add a cleanup job for production
- **Jonas profile**: seed data is inferred from public sources — review and edit via `/web/persona.html`
- **Auth**: no authentication — add API key middleware before exposing publicly

---

> Developed for Jonas Bailly — Jung von Matt HAVEL  
> Stack: FastAPI · Gemini · ChromaDB · SQLite · Vanilla JS
