import json

from flask import Blueprint, render_template, request

from kiosk_app.db import db_connection

offices_bp = Blueprint("offices", __name__)


def _with_files(row):
    """Return a plain dict from a sqlite3.Row with files parsed from JSON."""
    d = dict(row)
    try:
        d["files"] = json.loads(d.get("files") or "[]")
    except (ValueError, TypeError):
        d["files"] = []
    return d


@offices_bp.route("/office-selection")
def office_selection():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM offices"
            " WHERE expires_at IS NULL OR expires_at > datetime('now')"
            " ORDER BY id"
        ).fetchall()
    return render_template("office_selection.html", offices=rows)


@offices_bp.route("/office")
def office():
    office_key = request.args.get("name", "")
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM offices"
            " WHERE expires_at IS NULL OR expires_at > datetime('now')"
            " ORDER BY id"
        ).fetchall()
        row = conn.execute(
            "SELECT * FROM offices WHERE key = ?"
            " AND (expires_at IS NULL OR expires_at > datetime('now'))",
            (office_key,),
        ).fetchone()
        if row is None and rows:
            row = rows[0]

    offices = [_with_files(r) for r in rows]
    selected = _with_files(row) if row else {}
    return render_template("office.html", offices=offices, selected=selected)
