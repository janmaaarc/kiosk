import csv
import io
from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from kiosk_app.auth import login_required
from kiosk_app.db import db_connection
from kiosk_app.extensions import bcrypt, limiter

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", methods=["GET", "POST"])
@limiter.limit("5 per 15 minutes", methods=["POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if len(password) > 72:
            return render_template("admin_login.html")

        with db_connection() as conn:
            user = conn.execute(
                "SELECT password_hash FROM admins WHERE username=?",
                (username,),
            ).fetchone()

        if user and bcrypt.check_password_hash(user[0], password):
            with db_connection() as _sc:
                _row = _sc.execute(
                    "SELECT value FROM kiosk_settings WHERE key='admin_session_minutes'"
                ).fetchone()
            try:
                _mins = int(_row["value"]) if _row else 60
            except (ValueError, TypeError):
                _mins = 60
            session.clear()
            session["admin"] = username
            session["admin_expire"] = (
                datetime.utcnow().timestamp() + _mins * 60
            )
            current_app.logger.info("admin login ok: user=%s ip=%s", username, request.remote_addr)
            return redirect(url_for("admin.dashboard"))

        current_app.logger.warning("admin login failed: user=%s ip=%s", username, request.remote_addr)
        flash("Invalid username or password.", "error")

    return render_template("admin_login.html")


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with db_connection() as conn:
        scans_today = conn.execute(
            "SELECT COUNT(*) FROM rfid_logs WHERE scanned_at >= ?", (today,)
        ).fetchone()[0]
        try:
            searches_today = conn.execute(
                "SELECT COUNT(*) FROM search_logs WHERE searched_at >= ?", (today,)
            ).fetchone()[0]
            top_searches = [dict(r) for r in conn.execute(
                "SELECT query, COUNT(*) as cnt FROM search_logs"
                " WHERE searched_at >= date('now', '-7 days')"
                " GROUP BY LOWER(query) ORDER BY cnt DESC LIMIT 5"
            ).fetchall()]
        except Exception:
            searches_today = 0
            top_searches = []
        total_rooms = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
        total_faculty = conn.execute("SELECT COUNT(*) FROM faculty").fetchone()[0]
        active_announcements = conn.execute(
            "SELECT COUNT(*) FROM announcements"
            " WHERE (expires_at IS NULL OR expires_at > datetime('now'))"
        ).fetchone()[0]
        active_events = conn.execute(
            "SELECT COUNT(*) FROM events"
            " WHERE (expires_at IS NULL OR expires_at > datetime('now'))"
        ).fetchone()[0]
    return render_template("dashboard.html",
                           scans_today=scans_today,
                           searches_today=searches_today,
                           top_searches=top_searches,
                           total_rooms=total_rooms,
                           total_faculty=total_faculty,
                           active_announcements=active_announcements,
                           active_events=active_events)


@admin_bp.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin.admin_login"))


@admin_bp.route("/admin/settings", methods=["GET", "POST"])
@login_required
def kiosk_settings():
    _int_keys = {"idle_timeout_seconds", "screensaver_timeout_seconds",
                 "screensaver_slide_interval_ms", "admin_session_minutes"}
    with db_connection() as conn:
        if request.method == "POST":
            for key in _int_keys:
                val = request.form.get(key, "").strip()
                if val.isdigit() and int(val) > 0:
                    conn.execute(
                        "INSERT OR REPLACE INTO kiosk_settings (key, value) VALUES (?, ?)",
                        (key, val),
                    )
            conn.commit()
            flash("Settings saved.", "success")
            return redirect(url_for("admin.kiosk_settings"))
        rows = conn.execute("SELECT key, value FROM kiosk_settings").fetchall()
    settings = {r["key"]: r["value"] for r in rows}
    return render_template("admin/kiosk_settings.html", settings=settings)


@admin_bp.route("/rooms")
@login_required
def rooms():
    return redirect(url_for("content.rooms_list"))


@admin_bp.route("/add_room")
@login_required
def add_room():
    return redirect(url_for("content.room_add"))


@admin_bp.route("/edit_room/<int:room_id>")
@login_required
def edit_room(room_id: int):
    return redirect(url_for("content.room_edit", room_id=room_id))


@admin_bp.route("/delete_room/<int:id>", methods=["POST"])
@login_required
def delete_room(id: int):
    return redirect(url_for("content.rooms_list"))


@admin_bp.route("/rooms/import-csv", methods=["POST"])
@login_required
def rooms_import_csv():
    return redirect(url_for("content.rooms_list"))

