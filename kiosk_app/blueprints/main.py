from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

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
    return render_template("faculty.html")


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


@main_bp.route("/set_lang/<lang>", methods=["POST"])
def set_lang(lang: str):
    if lang in ("en", "fil"):
        session["lang"] = lang
    return redirect(url_for("main.menu"))
