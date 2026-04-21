from flask import Blueprint, abort, render_template, request

from kiosk_app.db import db_connection

announcements_bp = Blueprint("announcements", __name__)


@announcements_bp.route("/announcements")
def digital_announcements():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM announcements"
            " WHERE expires_at IS NULL OR expires_at > datetime('now')"
            " ORDER BY id DESC"
        ).fetchall()
    return render_template("digital_announcements.html", announcements=rows)


@announcements_bp.route("/announcement-view")
def announcement_view():
    file = request.args.get("file", "")
    with db_connection() as conn:
        row = conn.execute(
            "SELECT file FROM announcements WHERE file = ?"
            " AND (expires_at IS NULL OR expires_at > datetime('now'))",
            (file,),
        ).fetchone()
    if not row:
        abort(400)
    return render_template("announcement_view.html", file=row["file"])
