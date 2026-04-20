# FRAME — Cinema Blog
### Full-Stack App: Python (Flask) + SQLite + Vanilla JS

---

## Quick Start

### Prerequisites
- Python 3.10 or higher
- pip (comes with Python)

### Mac / Linux
```bash
chmod +x start.sh
./start.sh
```

### Windows
Double-click `start.bat`

### Then open:
```
http://localhost:5000
```

---

## Admin Panel

Click **Admin ↗** in the top-right nav, or go to `http://localhost:5000` and click it.

## Project Structure

```
frame-app/
├── backend/
│   ├── app.py          ← Flask API server
│   ├── requirements.txt
│   ├── frame.db        ← SQLite database (auto-created on first run)
│   └── uploads/        ← Uploaded images
├── frontend/
│   └── public/
│       └── index.html  ← Full SPA (public site + admin panel)
├── start.sh            ← Mac/Linux launcher
├── start.bat           ← Windows launcher
└── README.md
```

---

## Features

### Public Site
- **Home page** — Three section cards (Reviews, Alt. Endings, Film Stories)
- **Section pages** — Article listings with image + excerpt cards
- **Article pages** — Full blog post with cover image, star rating, rich content

### Admin Panel
- **Dashboard** — Stats overview + recent posts table
- **Per-section views** — Browse, filter by section
- **Article editor** — Write title, excerpt, body (HTML supported), set section, category, star rating
- **Cover images** — Upload from disk or paste a URL
- **Draft / Publish** — Toggle status per article
- **Delete** — With confirmation dialog

---

## API Endpoints

### Public
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/articles?section=reviews` | List published articles |
| GET | `/api/articles/:id` | Get single article |

### Admin (requires JWT token)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Login, get JWT |
| GET | `/api/admin/articles` | All articles (any status) |
| POST | `/api/admin/articles` | Create article |
| PUT | `/api/admin/articles/:id` | Update article |
| DELETE | `/api/admin/articles/:id` | Delete article |
| PATCH | `/api/admin/articles/:id/publish` | Toggle publish status |
| POST | `/api/admin/upload` | Upload cover image |
| GET | `/api/admin/stats` | Dashboard stats |

---

## Changing Admin Password

In `backend/app.py`, change these lines:

```python
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "frame2025")
```

Or run with environment variables:
```bash
ADMIN_USER=yourname ADMIN_PASS=yourpassword python3 app.py
```

---

## Deploying

For production deployment:
1. Set `JWT_SECRET` env var to a long random string
2. Change admin credentials
3. Use a production WSGI server like `gunicorn`:
   ```bash
   pip install gunicorn
   gunicorn -w 4 app:app
   ```
4. Put Nginx in front for static files and SSL

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3 + Flask |
| Database | SQLite (via stdlib `sqlite3`) |
| Auth | JWT (hand-rolled, no external deps) |
| Frontend | Vanilla JS SPA |
| Fonts | Playfair Display + DM Sans (Google Fonts) |
| Images | Local upload or external URL |
