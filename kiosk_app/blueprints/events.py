from flask import Blueprint, abort, render_template

from kiosk_app.db import db_connection

events_bp = Blueprint("events", __name__)


@events_bp.route("/events")
def events():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM events"
            " WHERE expires_at IS NULL OR expires_at > datetime('now')"
            " ORDER BY id DESC"
        ).fetchall()
    return render_template("events.html", events=rows)


@events_bp.route("/event/<int:event_id>")
def event_detail(event_id: int):
    with db_connection() as conn:
        event = conn.execute(
            "SELECT * FROM events WHERE id = ?"
            " AND (expires_at IS NULL OR expires_at > datetime('now'))",
            (event_id,),
        ).fetchone()
    if event is None:
        abort(404)
    return render_template("event_detail.html", event=event)
