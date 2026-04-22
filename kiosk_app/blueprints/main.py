import io
import os
from urllib.parse import quote

import qrcode
from flask import Blueprint, Response, jsonify, redirect, render_template, request, send_file

from kiosk_app.db import db_connection
from kiosk_app.extensions import csrf, limiter

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/menu")
def menu():
    return render_template("menu.html")


@main_bp.route("/faculty")
def faculty():
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM faculty ORDER BY name").fetchall()
    return render_template("faculty.html", faculty_list=[dict(r) for r in rows])


@main_bp.route("/rfid")
@limiter.limit("30 per minute")
def rfid():
    uid = request.args.get("uid", "").strip()
    if not uid:
        return redirect("/menu")
    with db_connection() as conn:
        row = conn.execute(
            "SELECT name, role FROM users WHERE rfid_uid = ?", (uid,)
        ).fetchone()
    if row:
        return render_template("profile.html", user_name=row["name"], user_role=row["role"])
    return redirect("/menu")


_RFID_LOCAL_ADDRS = frozenset({"127.0.0.1", "::1", "localhost"})


@main_bp.route("/check_rfid", methods=["POST"])
@csrf.exempt
@limiter.limit("60 per minute")
def check_rfid():
    # Only accept from localhost (the RFID watcher runs on the same host).
    if request.remote_addr not in _RFID_LOCAL_ADDRS:
        return jsonify({"status": "forbidden"}), 403
    data = request.get_json(silent=True) or {}
    uid = (data.get("uid") or "").strip()
    if not uid:
        return jsonify({"status": "error", "message": "missing uid"}), 400
    with db_connection() as conn:
        row = conn.execute(
            "SELECT name, role FROM users WHERE rfid_uid = ?", (uid,)
        ).fetchone()
    if row:
        return jsonify({"status": "authorized", "user": {"name": row["name"], "role": row["role"]}})
    return jsonify({"status": "unauthorized"})


@main_bp.route("/profile")
def profile():
    return render_template("profile.html")


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/search", methods=["GET", "POST"])
def search():
    result = None

    if request.method == "POST":
        room_number = request.form["room"]
        safe_prefix = room_number.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

        with db_connection() as conn:
            result = conn.execute(
                "SELECT * FROM rooms WHERE room LIKE ? ESCAPE '\\'",
                (safe_prefix + "%",),
            ).fetchone()

    return render_template("search.html", result=result)


@main_bp.route("/api/search")
@limiter.limit("60 per minute")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    results = []
    with db_connection() as conn:
        for row in conn.execute(
            "SELECT room, building FROM rooms WHERE room LIKE ? ESCAPE '\\' LIMIT 5",
            (pattern,),
        ).fetchall():
            results.append({"type": "room", "name": row["room"],
                            "building": row["building"] or "",
                            "url": "/search?room=" + quote(row["room"], safe="")})

        for row in conn.execute(
            "SELECT key, name FROM offices WHERE name LIKE ? ESCAPE '\\'"
            " AND (expires_at IS NULL OR expires_at > datetime('now')) LIMIT 5",
            (pattern,),
        ).fetchall():
            results.append({"type": "office", "name": row["name"],
                            "building": "",
                            "url": "/office?name=" + quote(row["key"], safe="")})

        for row in conn.execute(
            "SELECT name, department FROM faculty WHERE name LIKE ? ESCAPE '\\' LIMIT 5",
            (pattern,),
        ).fetchall():
            results.append({"type": "faculty", "name": row["name"],
                            "building": row["department"] or "",
                            "url": "/faculty"})

    return jsonify(results[:15])


@main_bp.route("/api/rooms")
@limiter.limit("60 per minute")
def api_rooms():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    safe_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT room FROM rooms WHERE room LIKE ? ESCAPE '\\' LIMIT 10",
            ("%" + safe_q + "%",),
        ).fetchall()
    return jsonify([row[0] for row in rows])


@main_bp.route("/offline")
def offline():
    return render_template("offline.html")


@main_bp.route("/qr")
@limiter.limit("60 per minute")
def qr_code():
    data = request.args.get("data", "").strip()
    if not data:
        return ("missing data", 400)
    try:
        size = max(64, min(int(request.args.get("size", 200)), 512))
    except (TypeError, ValueError):
        size = 200
    img = qrcode.make(data, box_size=max(1, size // 30), border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@main_bp.route("/sw.js")
def service_worker():
    sw_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "static", "sw.js",
    )
    try:
        with open(sw_path) as fh:
            body = fh.read()
    except FileNotFoundError:
        return ("service worker not found", 404)
    return Response(body, mimetype="application/javascript",
                    headers={"Service-Worker-Allowed": "/"})


@main_bp.route("/healthz")
def healthz():
    try:
        with db_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return jsonify({"status": "ok"}), 200
    except Exception:
        return jsonify({"status": "degraded"}), 503
