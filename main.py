"""
AdDigest — Advertising News Summarizer + Jonas Bailly AI Advisor
Run: uvicorn main:app --reload --port 8000
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("addigest")

# ── Init DB ──────────────────────────────────────────────
from modules.storage.database import get_db, init_db
from modules.storage.models import NewsItem, PersonaNote

init_db()

# ── Seed persona notes (once) ────────────────────────────
from modules.persona import notes_service as persona_svc
from modules.storage.database import SessionLocal


def _seed_persona():
    seed_path = Path("data/persona_seed.json")
    if not seed_path.exists():
        return
    db = SessionLocal()
    try:
        existing = db.query(PersonaNote).filter_by(is_seed=True).count()
        if existing > 0:
            return
        seeds = json.loads(seed_path.read_text())
        for s in seeds:
            persona_svc.create_note(
                db,
                title=s["title"],
                content=s["content"],
                tags=s.get("tags", []),
                is_seed=True,
            )
        logger.info(f"Seeded {len(seeds)} persona notes")
    except Exception as e:
        logger.warning(f"Persona seed failed: {e}")
    finally:
        db.close()


_seed_persona()

# ── FastAPI app ───────────────────────────────────────────
app = FastAPI(title="AdDigest — News Intelligence + Jonas AI Advisor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
if Path("web").exists():
    app.mount("/web", StaticFiles(directory="web", html=True), name="web")


# ════════════════════════════════════════════════════════════
# Pydantic Schemas
# ════════════════════════════════════════════════════════════

class NewsOut(BaseModel):
    id: int
    source: str
    title: str
    url: str
    summary: Optional[str] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NewsSearchRequest(BaseModel):
    keywords: list[str]
    sources: Optional[list[str]] = None


class LinkedInRequest(BaseModel):
    keywords: list[str]
    sources: Optional[list[str]] = None
    max_articles: int = 10


class PersonaNoteIn(BaseModel):
    title: str
    content: str
    tags: list[str] = []


class PersonaNoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None


class PersonaNoteOut(BaseModel):
    id: str
    title: str
    content: str
    tags: str
    is_seed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


# ════════════════════════════════════════════════════════════
# Startup / Scheduler
# ════════════════════════════════════════════════════════════

@app.on_event("startup")
def on_start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(_background_scrape, "interval", days=7)
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Weekly scheduler started")


def _background_scrape():
    """Silent background scrape using default keywords — stores to DB."""
    from modules.news import rss_collector, summarizer
    db = SessionLocal()
    try:
        items = rss_collector.collect_all()
        count = 0
        for it in items:
            if db.query(NewsItem).filter_by(url=it["url"]).first():
                continue
            summary = summarizer.summarize_article(it["content"])
            db.add(NewsItem(
                source=it["source"],
                title=it["title"],
                url=it["url"],
                summary=summary,
                content=it["content"],
                published_at=it["published_at"],
            ))
            db.commit()
            count += 1
        logger.info(f"Background scrape: inserted {count} new articles")
    except Exception as e:
        logger.error(f"Background scrape error: {e}")
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
# Health
# ════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    gemini_ok = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_CLOUD_PROJECT"))
    return {
        "status": "ok",
        "gemini_configured": gemini_ok,
        "time": datetime.utcnow().isoformat(),
    }


# ════════════════════════════════════════════════════════════
# News Endpoints
# ════════════════════════════════════════════════════════════

@app.get("/api/news", response_model=list[NewsOut])
def get_news(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return db.query(NewsItem).order_by(NewsItem.published_at.desc()).limit(limit).all()


@app.post("/api/scrape")
def scrape_now():
    """Trigger a manual scrape with default keywords."""
    from modules.news import rss_collector, summarizer
    db = SessionLocal()
    try:
        items = rss_collector.collect_all()
        inserted = 0
        for it in items:
            if db.query(NewsItem).filter_by(url=it["url"]).first():
                continue
            summary = summarizer.summarize_article(it["content"])
            db.add(NewsItem(
                source=it["source"], title=it["title"], url=it["url"],
                summary=summary, content=it["content"],
                published_at=it["published_at"],
            ))
            db.commit()
            inserted += 1
        return {"status": "ok", "found": len(items), "inserted": inserted,
                "timestamp": datetime.utcnow().isoformat()}
    finally:
        db.close()


@app.post("/api/digest")
def run_digest():
    """
    One-button full pipeline:
    Crawl ALL configured sources → filter last 7 days by default keywords
    → summarize → synthesize → generate LinkedIn article.
    No user input required.
    """
    from modules.news import rss_collector, summarizer, linkedin_generator

    lookback = int(os.getenv("WEEK_LOOKBACK_DAYS", "7"))
    items = rss_collector.collect_all(lookback_days=lookback)

    if not items:
        raise HTTPException(
            status_code=404,
            detail="No relevant articles found in the last 7 days across all sources."
        )

    items = items[:15]  # cap at 15 for quality

    summaries_meta = []
    for it in items:
        summary = summarizer.summarize_article(it["content"])
        summaries_meta.append({
            "title": it["title"],
            "summary": summary,
            "url": it["url"],
            "source": it["source"],
            "published_at": it["published_at"].isoformat(),
        })

    analysis = summarizer.synthesize_news(summaries_meta)
    article = linkedin_generator.generate_linkedin_article(
        keywords=rss_collector.DEFAULT_KEYWORDS,
        summaries_with_meta=summaries_meta,
        analysis=analysis,
    )

    return {
        "articles_found": len(summaries_meta),
        "articles": summaries_meta,
        "trend_analysis": analysis,
        "linkedin_article": article,
        "sources": [
            {"title": a["title"], "url": a["url"], "source": a["source"], "published_at": a["published_at"]}
            for a in summaries_meta
        ],
    }


@app.post("/api/news/search")
def search_news(req: NewsSearchRequest):
    """
    Search & summarize news by keywords. Returns articles with summaries.
    Does NOT store to DB — purely on-demand.
    """
    from modules.news import rss_collector, summarizer
    if not req.keywords:
        raise HTTPException(status_code=400, detail="keywords must not be empty")

    items = rss_collector.collect_all(
        keywords=req.keywords,
        sources=req.sources,
    )
    results = []
    for it in items[:20]:
        summary = summarizer.summarize_article(it["content"])
        results.append({
            "source": it["source"],
            "title": it["title"],
            "url": it["url"],
            "published_at": it["published_at"].isoformat(),
            "summary": summary,
            "relevance_score": round(it["score"], 3),
        })
    return {"keywords": req.keywords, "count": len(results), "articles": results}


@app.post("/api/news/generate-linkedin-article")
def generate_linkedin(req: LinkedInRequest):
    """
    Full pipeline: search → summarize → synthesize → generate LinkedIn article.
    """
    from modules.news import rss_collector, summarizer, linkedin_generator

    if not req.keywords:
        raise HTTPException(status_code=400, detail="keywords must not be empty")

    items = rss_collector.collect_all(keywords=req.keywords, sources=req.sources)
    items = items[:req.max_articles]

    if not items:
        raise HTTPException(status_code=404, detail="No relevant articles found for the given keywords")

    # Summarize each article
    summaries_meta = []
    for it in items:
        summary = summarizer.summarize_article(it["content"])
        summaries_meta.append({
            "title": it["title"],
            "summary": summary,
            "url": it["url"],
            "source": it["source"],
        })

    # Synthesize trends
    analysis = summarizer.synthesize_news(summaries_meta)

    # Generate LinkedIn article
    article = linkedin_generator.generate_linkedin_article(
        keywords=req.keywords,
        summaries_with_meta=summaries_meta,
        analysis=analysis,
    )

    return {
        "keywords": req.keywords,
        "articles_used": len(summaries_meta),
        "article_summaries": summaries_meta,
        "trend_analysis": analysis,
        "linkedin_article": article,
        "sources": [{"title": a["title"], "url": a["url"], "source": a["source"]} for a in summaries_meta],
    }


# ════════════════════════════════════════════════════════════
# Persona Notes Endpoints
# ════════════════════════════════════════════════════════════

@app.get("/api/persona/notes", response_model=list[PersonaNoteOut])
def list_notes(
    tag: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return persona_svc.list_notes(db, tag=tag)


@app.post("/api/persona/notes", response_model=PersonaNoteOut)
def create_note(body: PersonaNoteIn, db: Session = Depends(get_db)):
    return persona_svc.create_note(db, title=body.title, content=body.content, tags=body.tags)


@app.put("/api/persona/notes/{note_id}", response_model=PersonaNoteOut)
def update_note(note_id: str, body: PersonaNoteUpdate, db: Session = Depends(get_db)):
    note = persona_svc.update_note(db, note_id, title=body.title, content=body.content, tags=body.tags)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.delete("/api/persona/notes/{note_id}")
def delete_note(note_id: str, db: Session = Depends(get_db)):
    ok = persona_svc.delete_note(db, note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "deleted"}


@app.post("/api/rag/reindex")
def reindex(db: Session = Depends(get_db)):
    count = persona_svc.reindex_all(db)
    return {"status": "ok", "reindexed": count}


# ════════════════════════════════════════════════════════════
# Chat Endpoint
# ════════════════════════════════════════════════════════════

@app.post("/api/chat")
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    from modules.chat import chat_service
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")
    return chat_service.chat(db, message=body.message, conversation_id=body.conversation_id)
