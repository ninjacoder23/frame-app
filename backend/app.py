"""
FRAME Cinema Blog - Backend API
Python 3.10+ | Flask | SQLite | JWT Auth
"""
from dotenv import load_dotenv
load_dotenv()
import os
import sqlite3
import hashlib
import hmac
import json
import base64
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.serving import run_simple

# ── Minimal Flask-like WSGI app using only stdlib + werkzeug ──
# We use Flask if available, else raw WSGI
try:
    from flask import Flask, request, jsonify, send_from_directory, send_file
    from flask_cors import CORS
    USING_FLASK = True
except ImportError:
    USING_FLASK = False

if not USING_FLASK:
    try:
        from flask import Flask, request, jsonify, send_from_directory, send_file
        USING_FLASK = True
    except ImportError:
        pass

# ── Config ──
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, "frame.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
ADMIN_USER = os.environ.get("ADMIN_USER", "")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "")  
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

# CORS headers manually (no flask-cors needed)
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    return response

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        from flask import Response
        return Response(status=200)

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                id          TEXT PRIMARY KEY,
                section     TEXT NOT NULL CHECK(section IN ('reviews','endings','stories')),
                title       TEXT NOT NULL,
                excerpt     TEXT,
                body        TEXT,
                cover_image TEXT,
                stars       REAL,
                status      TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published')),
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                meta        TEXT DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_articles_section ON articles(section);
            CREATE INDEX IF NOT EXISTS idx_articles_status  ON articles(status);
        """)

init_db()

# ─────────────────────────────────────────────
# JWT  (manual — no flask-jwt-extended needed)
# ─────────────────────────────────────────────
def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def make_jwt(payload: dict, expire_hours=24) -> str:
    header  = b64url(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    payload["exp"] = int(time.time()) + expire_hours * 3600
    body    = b64url(json.dumps(payload).encode())
    sig     = b64url(hmac.new(JWT_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"

def verify_jwt(token: str) -> dict | None:
    try:
        h, b, s = token.split(".")
        expected = b64url(hmac.new(JWT_SECRET.encode(), f"{h}.{b}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(s, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(b + "=="))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if not token or not verify_jwt(token):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def row_to_dict(row):
    d = dict(row)
    if isinstance(d.get("meta"), str):
        try:
            d["meta"] = json.loads(d["meta"])
        except Exception:
            d["meta"] = {}
    return d

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(force=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if username == ADMIN_USER and password == ADMIN_PASS:
        token = make_jwt({"sub": username, "role": "admin"})
        return jsonify({"token": token, "username": username})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/auth/verify", methods=["GET"])
@require_auth
def verify():
    return jsonify({"ok": True})

# ─────────────────────────────────────────────
# PUBLIC ARTICLE ROUTES
# ─────────────────────────────────────────────
@app.route("/api/articles", methods=["GET"])
def list_articles():
    section = request.args.get("section")
    status  = request.args.get("status", "published")  # public only sees published
    with get_db() as conn:
        if section:
            rows = conn.execute(
                "SELECT * FROM articles WHERE section=? AND status=? ORDER BY created_at DESC",
                (section, status)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM articles WHERE status=? ORDER BY created_at DESC",
                (status,)
            ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/articles/<article_id>", methods=["GET"])
def get_article(article_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(row_to_dict(row))

# ─────────────────────────────────────────────
# ADMIN ARTICLE ROUTES
# ─────────────────────────────────────────────
@app.route("/api/admin/articles", methods=["GET"])
@require_auth
def admin_list_articles():
    section = request.args.get("section")
    with get_db() as conn:
        if section:
            rows = conn.execute(
                "SELECT * FROM articles WHERE section=? ORDER BY created_at DESC",
                (section,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM articles ORDER BY created_at DESC"
            ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/admin/articles", methods=["POST"])
@require_auth
def create_article():
    data = request.get_json(force=True) or {}
    article_id = str(uuid.uuid4())
    now = now_iso()
    required = ["section", "title"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400

    with get_db() as conn:
        conn.execute("""
            INSERT INTO articles (id, section, title, excerpt, body, cover_image, stars, status, created_at, updated_at, meta)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            article_id,
            data["section"],
            data["title"],
            data.get("excerpt", ""),
            data.get("body", ""),
            data.get("cover_image", ""),
            data.get("stars"),
            data.get("status", "draft"),
            now, now,
            json.dumps(data.get("meta", {}))
        ))
    return jsonify({"id": article_id, "created_at": now}), 201

@app.route("/api/admin/articles/<article_id>", methods=["PUT"])
@require_auth
def update_article(article_id):
    data = request.get_json(force=True) or {}
    now = now_iso()
    with get_db() as conn:
        row = conn.execute("SELECT id FROM articles WHERE id=?", (article_id,)).fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        fields = []
        values = []
        allowed = ["title","excerpt","body","cover_image","stars","status","section","meta"]
        for f in allowed:
            if f in data:
                fields.append(f"{f}=?")
                values.append(json.dumps(data[f]) if f == "meta" else data[f])
        fields.append("updated_at=?")
        values.append(now)
        values.append(article_id)
        conn.execute(f"UPDATE articles SET {','.join(fields)} WHERE id=?", values)
    return jsonify({"ok": True, "updated_at": now})

@app.route("/api/admin/articles/<article_id>", methods=["DELETE"])
@require_auth
def delete_article(article_id):
    with get_db() as conn:
        conn.execute("DELETE FROM articles WHERE id=?", (article_id,))
    return jsonify({"ok": True})

@app.route("/api/admin/articles/<article_id>/publish", methods=["PATCH"])
@require_auth
def toggle_publish(article_id):
    data = request.get_json(force=True) or {}
    status = data.get("status", "published")
    with get_db() as conn:
        conn.execute("UPDATE articles SET status=?, updated_at=? WHERE id=?",
                     (status, now_iso(), article_id))
    return jsonify({"ok": True, "status": status})

# ─────────────────────────────────────────────
# IMAGE UPLOAD
# ─────────────────────────────────────────────
@app.route("/api/admin/upload", methods=["POST"])
@require_auth
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if not f or not allowed_file(f.filename):
        return jsonify({"error": "Invalid file type"}), 400
    ext      = f.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4()}.{ext}"
    f.save(os.path.join(UPLOAD_DIR, filename))
    return jsonify({"url": f"/uploads/{filename}", "filename": filename}), 201

@app.route("/uploads/<filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ─────────────────────────────────────────────
# STATS (admin dashboard)
# ─────────────────────────────────────────────
@app.route("/api/admin/stats", methods=["GET"])
@require_auth
def stats():
    with get_db() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        published = conn.execute("SELECT COUNT(*) FROM articles WHERE status='published'").fetchone()[0]
        drafts    = conn.execute("SELECT COUNT(*) FROM articles WHERE status='draft'").fetchone()[0]
        by_section = conn.execute(
            "SELECT section, COUNT(*) as count FROM articles GROUP BY section"
        ).fetchall()
    return jsonify({
        "total": total,
        "published": published,
        "drafts": drafts,
        "by_section": {r["section"]: r["count"] for r in by_section}
    })

# ─────────────────────────────────────────────
# SERVE FRONTEND (production)
# ─────────────────────────────────────────────
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend", "public")

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path and os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")

# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("""
  ╔════════════════════════════════════╗
  ║   FRAME Cinema Blog — Backend      ║
  ║   Running on http://localhost:5000 ║       ║
  ╚════════════════════════════════════╝
    """)
    port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port, debug=False)
