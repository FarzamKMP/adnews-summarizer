"""
AdDigest Desktop Launcher
Starts the FastAPI server in background, opens browser, shows menu bar icon.
"""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


# ── Resolve base path (works both dev and PyInstaller bundle) ────────────────
if getattr(sys, "frozen", False):
    BASE_DIR  = Path(sys._MEIPASS)
    EXEC_DIR  = Path(sys.executable).parent   # Contents/MacOS — where .env & JSON live
    DATA_DIR  = Path(sys.executable).parent.parent.parent.parent / "AdDigest Data"
else:
    BASE_DIR  = Path(__file__).parent
    EXEC_DIR  = BASE_DIR
    DATA_DIR  = BASE_DIR

DATA_DIR.mkdir(exist_ok=True)

# Set working directory so relative paths in main.py resolve correctly
os.chdir(BASE_DIR)

# Inject env vars for writable user data paths
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DATA_DIR / 'news.db'}")
os.environ.setdefault("CHROMA_DIR",   str(DATA_DIR / "chroma_db"))

# Load .env — check EXEC_DIR first (inside bundle), then DATA_DIR
from dotenv import load_dotenv
for _ep in [EXEC_DIR / ".env", DATA_DIR / ".env", BASE_DIR / ".env"]:
    if _ep.exists():
        load_dotenv(_ep)
        break

# Fix relative credential path → absolute (search EXEC_DIR then BASE_DIR)
creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
if creds and not os.path.isabs(creds):
    creds_name = Path(creds).name
    for _search in [EXEC_DIR, BASE_DIR, DATA_DIR]:
        candidate = _search / creds_name
        if candidate.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(candidate)
            break

APP_URL = "http://127.0.0.1:8000/web/index.html"
PORT    = 8000


# ── Start uvicorn in background thread ───────────────────────────────────────
def start_server():
    import uvicorn
    # Import app directly so it works inside PyInstaller bundle
    from main import app
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()


# ── Wait until server is ready ───────────────────────────────────────────────
def wait_for_server(timeout=30):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


# ── System tray icon ──────────────────────────────────────────────────────────
def create_icon_image():
    """Create a simple coloured icon programmatically (no external file needed)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill="#5b7cfa")
    d.text((18, 18), "AD", fill="white")
    return img


def run_tray():
    import pystray

    def on_open(icon, item):
        webbrowser.open(APP_URL)

    def on_quit(icon, item):
        icon.stop()
        os._exit(0)

    icon = pystray.Icon(
        "AdDigest",
        create_icon_image(),
        "AdDigest",
        menu=pystray.Menu(
            pystray.MenuItem("Open AdDigest", on_open, default=True),
            pystray.MenuItem("Quit", on_quit),
        ),
    )
    icon.run()


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting AdDigest…")
    ready = wait_for_server()
    if ready:
        webbrowser.open(APP_URL)
    else:
        print("Server did not start in time.")
    run_tray()
