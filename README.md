# Playlist Drive Uploader

A Python (FastAPI) + React app that processes a fixed playlist of songs, searches YouTube for matching videos, scores each candidate for the right match, downloads audio (via a pluggable provider), uploads it to Google Drive, and shows the status of every song on a dashboard with a copy-able Drive link per file.

---

## 1. Prerequisites

- **Python** 3.11+
- **Node.js** 18+ and npm
- **ffmpeg** on PATH (required by the default `ytdlp` audio provider)
  - Windows: `winget install Gyan.FFmpeg` (or download a static build and add it to PATH)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - If you can't put ffmpeg on PATH, set `FFMPEG_LOCATION` in `.env` to the folder containing the binary.

---

## 2. Initial Setup

From the project root:

```bash
# 1. Install Python deps
python -m venv .venv
.\.venv\Scripts\activate         # Windows PowerShell
# source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt

# 2. Install Playwright's Chromium (used to scrape YouTube search results)
playwright install chromium

# 3. Install frontend deps
cd frontend
npm install
cd ..
```

---

## 3. Google Drive Credentials

1. In Google Cloud Console, create an **OAuth 2.0 Client ID** of type **Desktop app**.
2. Download the JSON and save it as **`credentials.json`** in the **project root** (next to this README).
3. The first time the app talks to Drive (either via the dashboard's **Drive Auth** button or automatically when the runner starts), a browser opens for consent. After approval, a **`token.json`** file is written to the project root and reused on subsequent runs.

Required scope (already configured in `backend/drive/auth.py`):

```
https://www.googleapis.com/auth/drive.file
```

The app:
- creates/finds a root folder named **`Playlist 3`** in your Drive (configurable via `GOOGLE_DRIVE_ROOT_FOLDER_NAME` in `.env`)
- creates/finds a sub-folder per playlist (e.g. `02_Lunch_Energy_12PM-130PM`)
- uploads each verified audio file there
- sets the file's permission to **anyone with the link can view**
- stores the Drive file ID + web link on the song row in the database

---

## 4. Seed the Database

Songs and playlists are seeded from `backend/seed_data.py` (the dataset baked into the PRD).

```bash
python -m backend.seed_data
```

The script is idempotent — re-running it adds new songs without duplicating existing ones, so you can safely edit the dataset and re-run.

---

## 5. Run the Backend

```bash
python -m uvicorn backend.main:app --reload
```

API is at `http://127.0.0.1:8000`. OpenAPI docs at `http://127.0.0.1:8000/docs`.

Key endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/status` | Aggregate counts + runner state |
| GET | `/api/songs` | All songs with their current status |
| GET | `/api/playlists` | Playlist progress summary |
| GET | `/api/logs?limit=500` | Recent log lines |
| GET | `/api/songs/{id}/candidates` | YouTube candidates for one song |
| POST | `/api/start` | Start the background runner |
| POST | `/api/pause` / `/api/resume` | Pause/resume the runner |
| POST | `/api/retry/{id}` | Retry a single song |
| POST | `/api/approve-candidate` | Pick a YouTube candidate during manual review |
| POST | `/api/skip/{id}` | Mark a song skipped |
| POST | `/api/drive/auth` | Trigger Drive OAuth (opens a browser on the backend host) |
| POST | `/api/drive/test` | Verify Drive connectivity |

---

## 6. Run the Frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://127.0.0.1:8000`, so the dev server and FastAPI run side by side.

The dashboard polls `/api/status` and `/api/songs` every 2 seconds for live updates.

### Dashboard Pages

- **Songs** — full table with status, confidence, YouTube match, Drive link, retry/skip actions, and runner controls (Start / Pause / Resume).
- **Playlists** — per-playlist progress bars.
- **Manual Review** — songs with confidence 70–84; pick the right candidate (with thumbnail, channel, duration, score) or retry the search.
- **Logs** — chronological INFO/WARNING/ERROR log entries.
- **Settings** — Drive auth + connection test.

---

## 7. How a Song Flows

For each song the runner:

1. **Search YouTube** — Playwright scrapes the public results page for the top 5 candidates (title, channel, duration, thumbnail, URL).
2. **Score** — `verification/match_scoring.py` produces a 0–100 confidence score using rapidfuzz, rewarding matches on song name / artist / requested modifiers (instrumental, piano, violin, remix, cover, clean) / official keywords / valid duration, and penalizing misleading terms (reaction, tutorial, lyrics, slowed, etc. — but never penalizing a modifier the user explicitly asked for).
3. **Confidence gate**
   - `>= 85` → auto-approved
   - `70–84` → marked **Needs Manual Review**
   - `< 70` → marked **Skipped - Low Confidence**
4. **Process audio** — the pluggable provider (default `ytdlp`) downloads the verified URL and produces an `.mp3` at `backend/temp_downloads/<track> - <song> - <artist>.mp3`.
5. **Verify file** — exists, > 500 KB, valid extension (`.mp3` / `.m4a` / `.wav`), reasonable duration (1–15 min) via `mutagen`.
6. **Upload to Drive** — find/create the playlist folder, upload (or reuse if same filename already exists in the folder), set "anyone with link can view", record the Drive file ID + web link.

Status transitions live in `backend/models.py::SongStatus`.

---

## 8. The Pluggable Audio Provider

`backend/automation/audio_processor.py` defines an `AudioProvider` interface and registers two built-ins:

| Name | Behavior |
|---|---|
| `ytdlp` (default) | Downloads via [yt-dlp](https://github.com/yt-dlp/yt-dlp) and converts to mp3 with ffmpeg. |
| `stub` | No-op — fails with a clear "not configured" error. Useful for dry-running the UI. |

Switch providers in `.env`:

```env
AUDIO_PROVIDER=ytdlp
```

To register a custom provider, add code that runs at backend startup:

```python
from backend.automation.audio_processor import register_provider, AudioProvider, AudioFetchResult

class MyProvider(AudioProvider):
    name = "mylib"
    def fetch(self, song, verified_url, target_path):
        # produce an audio file at target_path
        return AudioFetchResult(success=True, file_path=target_path)

register_provider(MyProvider())
```

Then set `AUDIO_PROVIDER=mylib`.

---

## 9. Reliability

- **Resume after crash** — re-running the backend skips songs already in `Completed` and respects existing failure / skipped states until you press **Retry** on the dashboard.
- **Per-song retries** — `MAX_RETRIES=2` (in `.env`) applies to user-initiated retries. The retry counter is stored on each song.
- **Duplicate prevention** — before uploading, the app checks (a) whether the song row already has a `drive_file_id` and (b) whether a file with the same name exists in the target Drive folder. Either match reuses the existing link instead of re-uploading.
- **Crash safety** — every status change commits to SQLite immediately.
- **Screenshots** — Playwright failures dump a screenshot to `backend/screenshots/` for debugging.
- **Structured logs** — every notable action writes a row to the `logs` table; the dashboard's Logs page reads from it live.

---

## 10. Configuration (`.env`)

| Key | Default | Notes |
|---|---|---|
| `APP_NAME` | `Playlist Drive Uploader` | Shown in API metadata |
| `GOOGLE_DRIVE_ROOT_FOLDER_NAME` | `Playlist 3` | Top-level Drive folder name |
| `LOCAL_TEMP_DOWNLOAD_FOLDER` | `backend/temp_downloads` | Audio scratch directory |
| `DATABASE_URL` | `sqlite:///./playlist.db` | SQLAlchemy URL |
| `AUTO_APPROVE_CONFIDENCE` | `85` | Threshold for auto-approval |
| `MANUAL_REVIEW_CONFIDENCE` | `70` | Below this → skipped |
| `MAX_RETRIES` | `2` | Per-song retry budget |
| `GOOGLE_CREDENTIALS_FILE` | `credentials.json` | OAuth client secrets |
| `GOOGLE_TOKEN_FILE` | `token.json` | Cached OAuth token |
| `AUDIO_PROVIDER` | `ytdlp` | `ytdlp` or `stub` (or your own) |
| `FFMPEG_LOCATION` | (empty) | Folder containing `ffmpeg` binary if not on PATH |
| `YTDLP_TIMEOUT_SECONDS` | `600` | Hard timeout for each yt-dlp download before the runner fails the song and continues |

---

## 11. Project Layout

```
project-root/
├── backend/
│   ├── main.py             # FastAPI app + endpoints
│   ├── config.py           # pydantic-settings, .env loader
│   ├── database.py         # SQLAlchemy session/engine
│   ├── models.py           # Playlist / Song / YouTubeCandidate / LogEntry
│   ├── seed_data.py        # Idempotent dataset seeder
│   ├── automation/
│   │   ├── youtube_search.py
│   │   ├── audio_processor.py   # pluggable providers (ytdlp + stub)
│   │   └── runner.py            # background pipeline + thread state
│   ├── verification/
│   │   ├── match_scoring.py
│   │   └── file_verification.py
│   ├── drive/
│   │   ├── auth.py
│   │   ├── folders.py
│   │   └── uploader.py
│   └── services/                # API serialization helpers
├── frontend/                    # Vite + React + Tailwind + shadcn-style UI
│   └── src/
│       ├── App.jsx
│       ├── pages/               # Songs / Playlists / Review / Logs / Settings
│       ├── components/
│       └── api/client.js
├── credentials.json             # YOU provide this
├── token.json                   # written on first auth
├── .env
├── requirements.txt
└── README.md
```

---

## 12. Troubleshooting

- **Windows Defender hangs on `.pyd` files** - run PowerShell as Administrator from the project root, then run `.\tools\add_defender_exclusions.ps1`. This excludes the virtualenv's compiled packages and Python's stdlib extension folder from Defender scans. The repo also sets `DISABLE_SQLALCHEMY_CEXT_RUNTIME=1` so SQLAlchemy uses its pure-Python fallback.
- **"ffmpeg not found"** — install ffmpeg or set `FFMPEG_LOCATION` in `.env`.
- **YouTube search returns no candidates** — check `backend/screenshots/` for a snapshot of the page; YouTube's consent wall or layout may have changed. Re-running the search usually works.
- **Drive auth crashes with `redirect_uri_mismatch`** — ensure the OAuth client is type **Desktop app**, not Web.
- **Drive upload fails with insufficient scope** — delete `token.json` and re-auth from the Settings page.
- **Database locked** — close any other process holding `playlist.db`. SQLAlchemy is configured for single-writer SQLite use.
- **Front-end shows nothing** — confirm uvicorn is running on port 8000 and that the proxy in `frontend/vite.config.js` matches.

---

## 13. Quick Reference

```bash
# Backend
python -m uvicorn backend.main:app --reload

# Seed
python -m backend.seed_data

# Frontend
cd frontend
npm run dev
```
