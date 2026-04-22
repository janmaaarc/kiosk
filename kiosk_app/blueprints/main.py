import os

from flask import Blueprint, Response, jsonify, redirect, render_template, request

from kiosk_app.db import db_connection
from kiosk_app.extensions import limiter

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
def rfid():
    return redirect("/menu")


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
                            "url": "/search?room=" + row["room"]})

        for row in conn.execute(
            "SELECT key, name FROM offices WHERE name LIKE ? ESCAPE '\\'"
            " AND (expires_at IS NULL OR expires_at > datetime('now')) LIMIT 5",
            (pattern,),
        ).fetchall():
            results.append({"type": "office", "name": row["name"],
                            "building": "",
                            "url": "/office?name=" + row["key"]})

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


@main_bp.route("/sw.js")
def service_worker():
    sw_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "static", "sw.js",
    )
    with open(sw_path) as fh:
        body = fh.read()
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
