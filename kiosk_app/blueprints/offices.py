import json

from flask import Blueprint, render_template, request

_VALID_BUILDING_URLS = frozenset([
    "/rodriguez_building", "/mist_ncestd_dorm", "/mist_ncestd_building",
    "/multi_purpose_building", "/power_room", "/ylagan_hall",
    "/automotive_building", "/academic_building", "/waf_&_rac_building",
    "/new_admin_building", "/old_admin_building", "/fsm_building",
    "/civil_tech_building", "/waf_&_fsm_building", "/tech_building",
    "/graduate_school_building", "/mechanical_building", "/te_building",
    "/science_building", "/it_building", "/engineering-floor1",
])

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
    raw_building = request.args.get("from_building", "")
    from_building = raw_building if raw_building in _VALID_BUILDING_URLS else ""
    return render_template(
        "office.html",
        offices=offices,
        selected=selected,
        from_building=from_building,
        from_floor=request.args.get("from_floor", "1"),
        from_room=request.args.get("from_room", selected.get("name", "")),
    )
