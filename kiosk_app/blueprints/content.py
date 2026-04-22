import json
import os
import uuid
from datetime import datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from kiosk_app.auth import login_required
from kiosk_app.db import db_connection
from kiosk_app.extensions import limiter

content_bp = Blueprint("content", __name__)

_UPLOAD_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "static", "uploads",
)
_ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_ALLOWED_FILE_MIME = {"application/pdf"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_FILE_BYTES = 10 * 1024 * 1024


def _parse_dt(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _safe_filename(original: str) -> str:
    ext = os.path.splitext(original)[1].lower()
    return uuid.uuid4().hex + ext


# ---------------------------------------------------------------------------
# Image / file upload
# ---------------------------------------------------------------------------

@content_bp.route("/admin/upload", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file provided"}), 400

    mime = f.mimetype or ""
    data = f.read()
    size = len(data)

    if mime in _ALLOWED_IMAGE_MIME:
        if size > _MAX_IMAGE_BYTES:
            return jsonify({"error": "Image exceeds 5 MB limit"}), 400
        subdir = "images"
    elif mime in _ALLOWED_FILE_MIME:
        if size > _MAX_FILE_BYTES:
            return jsonify({"error": "File exceeds 10 MB limit"}), 400
        subdir = "files"
    else:
        return jsonify({"error": "File type not allowed"}), 400

    dest_dir = os.path.join(_UPLOAD_ROOT, subdir)
    os.makedirs(dest_dir, exist_ok=True)
    filename = _safe_filename(f.filename)
    with open(os.path.join(dest_dir, filename), "wb") as fh:
        fh.write(data)

    return jsonify({"path": f"uploads/{subdir}/{filename}"})


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@content_bp.route("/admin/events")
@login_required
def events_list():
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY id DESC").fetchall()
    return render_template("admin/events.html", events=rows)


@content_bp.route("/admin/events/add", methods=["GET", "POST"])
@login_required
def event_add():
    if request.method == "POST":
        with db_connection() as conn:
            conn.execute(
                """INSERT INTO events
                   (title, image, desc, date, time, details, published_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.form["title"],
                    request.form.get("image", ""),
                    request.form.get("desc", ""),
                    request.form.get("date", ""),
                    request.form.get("time", ""),
                    request.form.get("details", ""),
                    _parse_dt(request.form.get("published_at", "")) or
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    _parse_dt(request.form.get("expires_at", "")),
                ),
            )
            conn.commit()
        return redirect(url_for("content.events_list"))
    return render_template("admin/event_form.html", event=None)


@content_bp.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def event_edit(event_id: int):
    with db_connection() as conn:
        event = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if event is None:
            abort(404)

        if request.method == "POST":
            conn.execute(
                """UPDATE events
                   SET title=?, image=?, desc=?, date=?, time=?,
                       details=?, published_at=?, expires_at=?
                   WHERE id=?""",
                (
                    request.form["title"],
                    request.form.get("image", ""),
                    request.form.get("desc", ""),
                    request.form.get("date", ""),
                    request.form.get("time", ""),
                    request.form.get("details", ""),
                    _parse_dt(request.form.get("published_at", "")) or
                    event["published_at"],
                    _parse_dt(request.form.get("expires_at", "")),
                    event_id,
                ),
            )
            conn.commit()
            return redirect(url_for("content.events_list"))

    return render_template("admin/event_form.html", event=event)


@content_bp.route("/admin/events/<int:event_id>/delete", methods=["POST"])
@login_required
def event_delete(event_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
    return redirect(url_for("content.events_list"))


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------

@content_bp.route("/admin/announcements")
@login_required
def announcements_list():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM announcements ORDER BY id DESC"
        ).fetchall()
    return render_template("admin/announcements.html", announcements=rows)


@content_bp.route("/admin/announcements/add", methods=["GET", "POST"])
@login_required
def announcement_add():
    if request.method == "POST":
        with db_connection() as conn:
            conn.execute(
                """INSERT INTO announcements
                   (title, thumbnail, file, published_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    request.form["title"],
                    request.form.get("thumbnail", ""),
                    request.form.get("file", ""),
                    _parse_dt(request.form.get("published_at", "")) or
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    _parse_dt(request.form.get("expires_at", "")),
                ),
            )
            conn.commit()
        return redirect(url_for("content.announcements_list"))
    return render_template("admin/announcement_form.html", announcement=None)


@content_bp.route("/admin/announcements/<int:ann_id>/edit", methods=["GET", "POST"])
@login_required
def announcement_edit(ann_id: int):
    with db_connection() as conn:
        ann = conn.execute(
            "SELECT * FROM announcements WHERE id = ?", (ann_id,)
        ).fetchone()
        if ann is None:
            abort(404)

        if request.method == "POST":
            conn.execute(
                """UPDATE announcements
                   SET title=?, thumbnail=?, file=?, published_at=?, expires_at=?
                   WHERE id=?""",
                (
                    request.form["title"],
                    request.form.get("thumbnail", ""),
                    request.form.get("file", ""),
                    _parse_dt(request.form.get("published_at", "")) or
                    ann["published_at"],
                    _parse_dt(request.form.get("expires_at", "")),
                    ann_id,
                ),
            )
            conn.commit()
            return redirect(url_for("content.announcements_list"))

    return render_template("admin/announcement_form.html", announcement=ann)


@content_bp.route("/admin/announcements/<int:ann_id>/delete", methods=["POST"])
@login_required
def announcement_delete(ann_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM announcements WHERE id = ?", (ann_id,))
        conn.commit()
    return redirect(url_for("content.announcements_list"))


# ---------------------------------------------------------------------------
# Offices
# ---------------------------------------------------------------------------

@content_bp.route("/admin/offices")
@login_required
def offices_list():
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM offices ORDER BY id").fetchall()
    return render_template("admin/offices.html", offices=rows)


@content_bp.route("/admin/offices/add", methods=["GET", "POST"])
@login_required
def office_add():
    if request.method == "POST":
        with db_connection() as conn:
            conn.execute(
                """INSERT INTO offices
                   (key, name, image, location, hours, desc, files, building_url,
                    published_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.form["key"],
                    request.form["name"],
                    request.form.get("image", ""),
                    request.form.get("location", ""),
                    request.form.get("hours", ""),
                    request.form.get("desc", ""),
                    "[]",
                    request.form.get("building_url", ""),
                    _parse_dt(request.form.get("published_at", "")) or
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    _parse_dt(request.form.get("expires_at", "")),
                ),
            )
            conn.commit()
        return redirect(url_for("content.offices_list"))
    return render_template("admin/office_form.html", office=None)


@content_bp.route("/admin/offices/<int:office_id>/edit", methods=["GET", "POST"])
@login_required
def office_edit(office_id: int):
    with db_connection() as conn:
        office = conn.execute(
            "SELECT * FROM offices WHERE id = ?", (office_id,)
        ).fetchone()
        if office is None:
            abort(404)

        if request.method == "POST":
            conn.execute(
                """UPDATE offices
                   SET key=?, name=?, image=?, location=?, hours=?, desc=?,
                       files=COALESCE(files, '[]'), building_url=?,
                       published_at=?, expires_at=?
                   WHERE id=?""",
                (
                    request.form["key"],
                    request.form["name"],
                    request.form.get("image", ""),
                    request.form.get("location", ""),
                    request.form.get("hours", ""),
                    request.form.get("desc", ""),
                    request.form.get("building_url", ""),
                    _parse_dt(request.form.get("published_at", "")) or
                    office["published_at"],
                    _parse_dt(request.form.get("expires_at", "")),
                    office_id,
                ),
            )
            conn.commit()
            return redirect(url_for("content.offices_list"))

    return render_template("admin/office_form.html", office=office)


@content_bp.route("/admin/offices/<int:office_id>/delete", methods=["POST"])
@login_required
def office_delete(office_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM offices WHERE id = ?", (office_id,))
        conn.commit()
    return redirect(url_for("content.offices_list"))


# ---------------------------------------------------------------------------
# Building Floors
# ---------------------------------------------------------------------------

@content_bp.route("/admin/building-floors")
@login_required
def building_floors_list():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM building_floors ORDER BY building, floor_number"
        ).fetchall()
    return render_template("admin/building_floors.html", floors=rows)


@content_bp.route("/admin/building-floors/add", methods=["GET", "POST"])
@login_required
def building_floor_add():
    if request.method == "POST":
        with db_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO building_floors
                   (building, floor_number, floor_label, floor_image)
                   VALUES (?, ?, ?, ?)""",
                (
                    request.form["building"],
                    int(request.form["floor_number"]),
                    request.form["floor_label"],
                    request.form.get("floor_image", ""),
                ),
            )
            conn.commit()
        return redirect(url_for("content.building_floors_list"))
    return render_template("admin/building_floor_form.html", floor=None)


@content_bp.route("/admin/building-floors/<int:floor_id>/edit", methods=["GET", "POST"])
@login_required
def building_floor_edit(floor_id: int):
    with db_connection() as conn:
        floor = conn.execute(
            "SELECT * FROM building_floors WHERE id = ?", (floor_id,)
        ).fetchone()
        if floor is None:
            abort(404)

        if request.method == "POST":
            conn.execute(
                """UPDATE building_floors
                   SET building=?, floor_number=?, floor_label=?, floor_image=?
                   WHERE id=?""",
                (
                    request.form["building"],
                    int(request.form["floor_number"]),
                    request.form["floor_label"],
                    request.form.get("floor_image", ""),
                    floor_id,
                ),
            )
            conn.commit()
            return redirect(url_for("content.building_floors_list"))

    return render_template("admin/building_floor_form.html", floor=floor)


@content_bp.route("/admin/building-floors/<int:floor_id>/delete", methods=["POST"])
@login_required
def building_floor_delete(floor_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM building_floors WHERE id = ?", (floor_id,))
        conn.commit()
    return redirect(url_for("content.building_floors_list"))


# ---------------------------------------------------------------------------
# Faculty
# ---------------------------------------------------------------------------

@content_bp.route("/admin/faculty")
@login_required
def faculty_list():
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM faculty ORDER BY name").fetchall()
    return render_template("admin/faculty_list.html", faculty=rows)


@content_bp.route("/admin/faculty/add", methods=["GET", "POST"])
@login_required
def faculty_add():
    if request.method == "POST":
        with db_connection() as conn:
            conn.execute(
                """INSERT INTO faculty
                   (name, department, position, photo, schedule_image,
                    room, building, office_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.form["name"],
                    request.form.get("department", ""),
                    request.form.get("position", ""),
                    request.form.get("photo", ""),
                    request.form.get("schedule_image", ""),
                    request.form.get("room", ""),
                    request.form.get("building", ""),
                    request.form.get("office_key", ""),
                ),
            )
            conn.commit()
        return redirect(url_for("content.faculty_list"))
    return render_template("admin/faculty_form.html", member=None)


@content_bp.route("/admin/faculty/<int:member_id>/edit", methods=["GET", "POST"])
@login_required
def faculty_edit(member_id: int):
    with db_connection() as conn:
        member = conn.execute(
            "SELECT * FROM faculty WHERE id = ?", (member_id,)
        ).fetchone()
        if member is None:
            abort(404)

        if request.method == "POST":
            conn.execute(
                """UPDATE faculty
                   SET name=?, department=?, position=?, photo=?,
                       schedule_image=?, room=?, building=?, office_key=?
                   WHERE id=?""",
                (
                    request.form["name"],
                    request.form.get("department", ""),
                    request.form.get("position", ""),
                    request.form.get("photo", ""),
                    request.form.get("schedule_image", ""),
                    request.form.get("room", ""),
                    request.form.get("building", ""),
                    request.form.get("office_key", ""),
                    member_id,
                ),
            )
            conn.commit()
            return redirect(url_for("content.faculty_list"))

    return render_template("admin/faculty_form.html", member=member)


@content_bp.route("/admin/faculty/<int:member_id>/delete", methods=["POST"])
@login_required
def faculty_delete(member_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM faculty WHERE id = ?", (member_id,))
        conn.commit()
    return redirect(url_for("content.faculty_list"))
