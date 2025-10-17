# 📰 AdDigest — Advertising News Scraper & Summarizer

AdDigest automatically collects, summarizes, and displays the latest advertising & marketing news.  
Built with FastAPI, Gunicorn + Uvicorn, SQLite, and Nginx, with optional AI summaries via Gemini.

---

## 🚀 Features
- RSS aggregation from top marketing & advertising sites  
- Full-text extraction with `newspaper3k`  
- AI summarization using Google Gemini (optional)  
- Weekly scheduled scraping (APScheduler)  
- RESTful FastAPI API (`/api/health`, `/api/scrape`, `/api/news`)  
- Minimal HTML/JS frontend served by Nginx  

---

## ⚙️ Quick Setup
```bash
git clone https://github.com/<your-username>/adnews-summarizer.git
cd adnews-summarizer
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m nltk.downloader punkt
uvicorn main:app --reload --port 8000
````

**Test locally**

```
GET  http://127.0.0.1:8000/api/health
POST http://127.0.0.1:8000/api/scrape
GET  http://127.0.0.1:8000/api/news
```

---

## 🖥️ VPS Deployment

### 1️⃣ Backend (systemd)

Create `/etc/systemd/system/adnews.service`:

```ini
[Unit]
Description=AdNews FastAPI
After=network.target

[Service]
User=root
WorkingDirectory=/root/adnews-summarizer
ExecStart=/root/adnews-summarizer/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now adnews
```

### 2️⃣ Frontend (Nginx)

```bash
sudo mkdir -p /var/www/adnews
sudo cp -r web/* /var/www/adnews/
```

Create `/etc/nginx/sites-available/adnews`:

```nginx
server {
    listen 80;
    server_name _;

    location / {
        root /var/www/adnews;
        index index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/adnews /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

---

## 🧪 API Endpoints

| Method | Endpoint      | Description                  |
| ------ | ------------- | ---------------------------- |
| `GET`  | `/api/health` | Health check & Gemini status |
| `POST` | `/api/scrape` | Trigger scraping manually    |
| `GET`  | `/api/news`   | Fetch latest articles        |

Example:

```bash
curl -X POST http://<SERVER-IP>/api/scrape
```

Response:

```json
{"status":"ok","found":50,"inserted":3,"timestamp":"2025-10-17T12:00:00Z"}
```

---

## 🧭 Debug & Maintenance

| Task             | Command                                    |
| ---------------- | ------------------------------------------ |
| View logs        | `sudo journalctl -u adnews -f`             |
| Check Nginx      | `sudo tail -n 50 /var/log/nginx/error.log` |
| Restart services | `sudo systemctl restart adnews nginx`      |
| Sync frontend    | `sudo rsync -a web/ /var/www/adnews/`      |

---

## 🔧 Customize

* Add or remove feeds → edit `SITES_RSS` in `main.py`
* Update keywords → edit `KEYWORDS` list
* Change schedule:

  ```python
  scheduler.add_job(run_full_cycle, "interval", days=7)
  ```

---

## 🧑‍💻 License

> Developed for <a href="https://de.linkedin.com/in/jonas-bailly-69793914">Jonas Bailly</a>
> Made with ❤️ using FastAPI, Gemini, and Nginx.
