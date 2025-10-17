# uvicorn main:app --reload --port 8000
# http://127.0.0.1:8000/api/health = Gemini Connection test
# http://127.0.0.1:8000/api/scrape = Trigger scraping now
# http://127.0.0.1:8000/api/news = Get latest news

import logging
import re
import time
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from newspaper import Article
from apscheduler.schedulers.background import BackgroundScheduler

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# -----------------------------
# Gemini مستقیم
# -----------------------------
USE_GEMINI = False
try:
    import google.generativeai as genai
    GEMINI_API_KEY = "YOUR GEMNINI API KEY HERE"  # جایگزین کن
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        USE_GEMINI = True
except Exception as e:
    print("Gemini import failed:", e)
    USE_GEMINI = False

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ads-news-scraper")

DATABASE_URL = "sqlite:///./news.db"
WEEK_LOOKBACK_DAYS = 7

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# -----------------------------
# RSS دقیق سایت‌ها
# -----------------------------
SITES_RSS = {
    "adweek": "https://www.adweek.com/feed/",
    "adage": "https://adage.com/section/marketing-news/rss",
    "digiday": "https://digiday.com/feed/",
    "marketingweek": "https://www.marketingweek.com/feed/",
    "campaignlive": "https://www.campaignlive.co.uk/rss/",
    "warc": "https://www.warc.com/rss",
    "wuv": "https://www.wuv.de/rss/",
    "horizont": "https://www.horizont.net/rss/",
}

# -----------------------------
# Keywords مرتبط با تبلیغات
# -----------------------------
KEYWORDS = ["advertising", "marketing", "campaign", "brand", "creative", "agency", "digital", "social media"]

# -----------------------------
# مدل پایگاه داده
# -----------------------------
class NewsItem(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    source = Column(String(255))
    title = Column(String(1000))
    url = Column(String(2000), unique=True)
    summary = Column(Text)
    content = Column(Text)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# -----------------------------
# اسکیمای خروجی API
# -----------------------------
class NewsOut(BaseModel):
    id: int
    source: str
    title: str
    url: str
    summary: Optional[str]
    published_at: Optional[datetime]

    class Config:
        orm_mode = True

# -----------------------------
# DB Session
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# جمع‌آوری اخبار از RSS
# -----------------------------
def collect_from_rss(name, rss_url):
    logger.info(f"Collecting from {name} ({rss_url})")
    items = []
    feed = feedparser.parse(rss_url)
    cutoff = datetime.utcnow() - timedelta(days=WEEK_LOOKBACK_DAYS)
    for entry in feed.entries:
        link = entry.get("link")
        if not link:
            continue
        pub = datetime.utcnow()
        if hasattr(entry, "published_parsed"):
            pub = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        if pub < cutoff:
            continue

        try:
            art = Article(link)
            art.download()
            art.parse()
            content = art.text.strip()
            title = art.title.strip()
            if len(content) < 100:
                continue

            # فیلتر مرتبط بودن با تبلیغات
            text_to_check = (title + " " + content).lower()
            if not any(k.lower() in text_to_check for k in KEYWORDS):
                continue

            items.append({
                "source": name,
                "title": title,
                "url": link,
                "content": content,
                "published_at": pub
            })
        except Exception as e:
            logger.warning(f"Failed to parse {link}: {e}")

    logger.info(f"{name}: Found {len(items)} relevant articles")
    return items

# -----------------------------
# خلاصه‌سازی
# -----------------------------
def summarize_text(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if USE_GEMINI:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"Summarize this marketing or advertising article in 3 concise sentences:\n\n{text}"
            res = model.generate_content(prompt)
            return res.text.strip()
        except Exception as e:
            logger.warning(f"Gemini summarization failed: {e}")
    # fallback ساده
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return " ".join(sentences[:3])[:800]

# -----------------------------
# ذخیره در DB
# -----------------------------
def store_items(db, items):
    count = 0
    for it in items:
        if db.query(NewsItem).filter_by(url=it["url"]).first():
            continue
        summary = summarize_text(it["content"])
        news = NewsItem(
            source=it["source"],
            title=it["title"],
            url=it["url"],
            summary=summary,
            content=it["content"],
            published_at=it["published_at"]
        )
        db.add(news)
        db.commit()
        count += 1
    logger.info(f"Inserted {count} new articles")
    return count

# -----------------------------
# اجرای کامل
# -----------------------------
def run_full_cycle():
    db = SessionLocal()
    total_found = 0
    total_inserted = 0
    try:
        for name, rss_url in SITES_RSS.items():
            items = collect_from_rss(name, rss_url)
            total_found += len(items)
            inserted = store_items(db, items)
            total_inserted += inserted
    finally:
        db.close()
    logger.info(f"Cycle complete: found {total_found}, inserted {total_inserted}")
    return {"found": total_found, "inserted": total_inserted, "timestamp": datetime.utcnow().isoformat()}

# -----------------------------
# FastAPI
# -----------------------------
app = FastAPI(title="Advertising News Summarizer (Gemini-powered)")

# --- اجازه CORS برای فرانت‌ات ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # اگر خواستی امنیتی‌تر باشه: ["http://127.0.0.1:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_full_cycle, "interval", days=7, next_run_time=datetime.utcnow())
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Scheduler started: runs weekly")

@app.get("/api/news", response_model=List[NewsOut])
def get_news(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    news = db.query(NewsItem).order_by(NewsItem.published_at.desc()).limit(limit).all()
    return news

@app.post("/api/scrape")
def scrape_now():
    result = run_full_cycle()
    return {"status": "ok", **result}

@app.get("/api/health")
def health():
    return {"status": "ok", "use_gemini": USE_GEMINI, "time": datetime.utcnow().isoformat()}