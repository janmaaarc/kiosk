import csv
import io
import json
import os
import sqlite3
import uuid
from datetime import datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
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

_STATIC_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static")

_DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
_TIMES = ["7:00","8:00","9:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00"]

_VALID_DAYS       = {"MON","TUE","WED","THU","FRI","SAT"}
_VALID_COLORS     = {"yellow","green","blue","teal","red","purple"}
_VALID_USER_ROLES = {"student", "faculty", "visitor"}

def _parse_schedule_form(form) -> list:
    entries = []
    days    = form.getlist("sched_day")
    starts  = form.getlist("sched_start")
    ends    = form.getlist("sched_end")
    subjs   = form.getlist("sched_subject")
    rooms   = form.getlist("sched_room")
    colors  = form.getlist("sched_color")
    for i, day in enumerate(days):
        if day not in _VALID_DAYS:
            continue
        if i >= len(subjs) or not subjs[i].strip():
            continue
        color = colors[i] if i < len(colors) else "yellow"
        if color not in _VALID_COLORS:
            color = "yellow"
        entries.append({
            "day":     day,
            "start":   starts[i] if i < len(starts) else "",
            "end":     ends[i]   if i < len(ends)   else "",
            "subject": subjs[i].strip(),
            "room":    rooms[i].strip() if i < len(rooms) else "",
            "color":   color,
        })
    return entries

_UPLOAD_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "static", "uploads",
)
_ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_ALLOWED_FILE_MIME = {"application/pdf"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_FILE_BYTES = 10 * 1024 * 1024

_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),
    (b"%PDF", "application/pdf"),
]


def _sniff_mime(stream) -> str:
    header = stream.read(12)
    stream.seek(0)
    for magic, mime in _MAGIC_BYTES:
        if header.startswith(magic):
            if mime == "image/webp" and b"WEBP" not in header:
                continue
            return mime
    return ""


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


import re as _re
_SAFE_FILE_RE = _re.compile(r'^(?:uploads|files/uploads)/[0-9a-f]{32}\.pdf$')
_HEX_COLOR_RE = _re.compile(r'^#[0-9a-fA-F]{6}$')
_ALLOWED_ROOM_COLORS = {'', 'cr', 'fire-exit', 'elevator'}

def _sanitize_room_color(value: str) -> str:
    v = value.strip()
    if v in _ALLOWED_ROOM_COLORS or _HEX_COLOR_RE.match(v):
        return v
    return ''
_SAFE_IMAGE_PATH_RE = _re.compile(r'^(uploads/images/[0-9a-f]{32}|images/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+)\.(jpg|jpeg|png|webp|gif|JPG|JPEG|PNG|WEBP|GIF)$')


def _safe_files_json(raw: str) -> str:
    """Validate and sanitize files JSON array; returns '[]' on any error."""
    try:
        items = json.loads(raw or "[]")
        if not isinstance(items, list):
            return "[]"
        safe = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()[:200]
            path = str(item.get("file", "")).strip()
            if title and _SAFE_FILE_RE.fullmatch(path):
                safe.append({"title": title, "file": path})
        return json.dumps(safe)
    except (ValueError, TypeError):
        return "[]"


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

    mime = _sniff_mime(f.stream)
    data = f.read()
    size = len(data)

    if mime in _ALLOWED_IMAGE_MIME:
        if size > _MAX_IMAGE_BYTES:
            return jsonify({"error": "Image exceeds 5 MB limit"}), 400
        subdir = "images"
    elif mime in _ALLOWED_FILE_MIME:
        if size > _MAX_FILE_BYTES:
            return jsonify({"error": "File exceeds 10 MB limit"}), 400
        # PDFs go under static/files/uploads/ so openPDF('/static/files/' + path) works
        _FILES_ROOT = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "static", "files", "uploads",
        )
        os.makedirs(_FILES_ROOT, exist_ok=True)
        filename = _safe_filename(f.filename)
        with open(os.path.join(_FILES_ROOT, filename), "wb") as fh:
            fh.write(data)
        return jsonify({"path": f"uploads/{filename}"})
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
    per  = 20
    with db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        total_pages = max(1, -(-total // per))
        page = max(1, min(request.args.get("page", 1, type=int), total_pages))
        rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ? OFFSET ?",
                            (per, (page - 1) * per)).fetchall()
    return render_template("admin/events.html", events=rows,
                           page=page, total_pages=total_pages)


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
        flash("Event saved.", "success")
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
            flash("Event updated.", "success")
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
    per  = 20
    with db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
        total_pages = max(1, -(-total // per))
        page = max(1, min(request.args.get("page", 1, type=int), total_pages))
        rows = conn.execute("SELECT * FROM announcements ORDER BY id ASC LIMIT ? OFFSET ?",
                            (per, (page - 1) * per)).fetchall()
    return render_template("admin/announcements.html", announcements=rows,
                           page=page, total_pages=total_pages)


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
        flash("Announcement saved.", "success")
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
            flash("Announcement updated.", "success")
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
    per = 30
    with db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM offices").fetchone()[0]
        total_pages = max(1, -(-total // per))
        page = max(1, min(request.args.get("page", 1, type=int), total_pages))
        rows = conn.execute(
            "SELECT * FROM offices ORDER BY id LIMIT ? OFFSET ?",
            (per, (page - 1) * per),
        ).fetchall()
    return render_template("admin/offices.html", offices=rows, page=page, total_pages=total_pages)


@content_bp.route("/admin/offices/add", methods=["GET", "POST"])
@login_required
def office_add():
    if request.method == "POST":
        with db_connection() as conn:
            visible_roles = request.form.getlist("visible_to")
            _ALLOWED_ROLES = {"student", "faculty", "visitor"}
            safe_roles = [r for r in visible_roles if r in _ALLOWED_ROLES]
            visible_to = "," + ",".join(safe_roles) + "," if safe_roles else ",student,faculty,visitor,"
            conn.execute(
                """INSERT INTO offices
                   (key, name, image, location, hours, desc, files, building_url,
                    visible_to, published_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.form["key"],
                    request.form["name"],
                    request.form.get("image", ""),
                    request.form.get("location", ""),
                    request.form.get("hours", ""),
                    request.form.get("desc", ""),
                    _safe_files_json(request.form.get("files_json", "[]")),
                    request.form.get("building_url", ""),
                    visible_to,
                    _parse_dt(request.form.get("published_at", "")) or
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    _parse_dt(request.form.get("expires_at", "")),
                ),
            )
            conn.commit()
        flash("Office saved.", "success")
        return redirect(url_for("content.offices_list"))
    return render_template("admin/office_form.html", office=None, staff=[])


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
            visible_roles = request.form.getlist("visible_to")
            _ALLOWED_ROLES = {"student", "faculty", "visitor"}
            safe_roles = [r for r in visible_roles if r in _ALLOWED_ROLES]
            visible_to = "," + ",".join(safe_roles) + "," if safe_roles else ",student,faculty,visitor,"
            conn.execute(
                """UPDATE offices
                   SET key=?, name=?, image=?, location=?, hours=?, desc=?,
                       files=?, building_url=?, visible_to=?,
                       published_at=?, expires_at=?
                   WHERE id=?""",
                (
                    request.form["key"],
                    request.form["name"],
                    request.form.get("image", ""),
                    request.form.get("location", ""),
                    request.form.get("hours", ""),
                    request.form.get("desc", ""),
                    _safe_files_json(request.form.get("files_json", office["files"] or "[]")),
                    request.form.get("building_url", ""),
                    visible_to,
                    _parse_dt(request.form.get("published_at", "")) or
                    office["published_at"],
                    _parse_dt(request.form.get("expires_at", "")),
                    office_id,
                ),
            )
            conn.commit()

            # Update office_position — only for faculty that belong to this office
            staff_rows = conn.execute(
                "SELECT id FROM faculty WHERE office_key = ?", (office["key"],)
            ).fetchall()
            valid_ids = {r["id"] for r in staff_rows}
            for key, val in request.form.items():
                if key.startswith("staff_position[") and key.endswith("]"):
                    try:
                        fid = int(key[15:-1])
                    except ValueError:
                        continue
                    if fid not in valid_ids:
                        continue
                    conn.execute(
                        "UPDATE faculty SET office_position=? WHERE id=?",
                        (val.strip(), fid),
                    )
            conn.commit()
            flash("Office updated.", "success")
            return redirect(url_for("content.offices_list"))

        staff = [dict(r) for r in conn.execute(
            "SELECT id, name, office_position FROM faculty"
            " WHERE office_key = ? ORDER BY office_position, name",
            (office["key"],),
        ).fetchall()]

    return render_template("admin/office_form.html", office=office, staff=staff)


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

def _get_buildings() -> list[str]:
    with db_connection() as conn:
        rows = conn.execute("SELECT name FROM buildings ORDER BY name").fetchall()
        if rows:
            return [r[0] for r in rows]
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT building FROM building_floors ORDER BY building"
        ).fetchall()]


@content_bp.route("/admin/buildings")
@login_required
def buildings_list():
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM buildings ORDER BY name").fetchall()
    return render_template("admin/buildings.html", buildings=rows)


@content_bp.route("/admin/buildings/add", methods=["GET", "POST"])
@login_required
def building_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Building name is required.", "error")
            return redirect(url_for("content.building_add"))
        image_raw = request.form.get("image", "").strip()
        image = image_raw if image_raw and _SAFE_IMAGE_PATH_RE.fullmatch(image_raw) else None
        with db_connection() as conn:
            try:
                conn.execute("INSERT INTO buildings (name, image) VALUES (?, ?)", (name, image))
                conn.commit()
            except Exception:
                flash("A building with that name already exists.", "error")
                return redirect(url_for("content.building_add"))
        flash("Building added.", "success")
        return redirect(url_for("content.buildings_list"))
    return render_template("admin/building_form.html", building=None)


@content_bp.route("/admin/buildings/<int:building_id>/edit", methods=["GET", "POST"])
@login_required
def building_edit(building_id: int):
    with db_connection() as conn:
        building = conn.execute(
            "SELECT * FROM buildings WHERE id = ?", (building_id,)
        ).fetchone()
        if building is None:
            abort(404)
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Building name is required.", "error")
                return redirect(url_for("content.building_edit", building_id=building_id))
            try:
                conn.execute(
                    "UPDATE buildings SET name = ? WHERE id = ?",
                    (name, building_id)
                )
                conn.commit()
            except Exception:
                flash("A building with that name already exists.", "error")
                return redirect(url_for("content.building_edit", building_id=building_id))
            flash("Building updated.", "success")
            return redirect(url_for("content.buildings_list"))
    return render_template("admin/building_form.html", building=building)


@content_bp.route("/admin/buildings/<int:building_id>/delete", methods=["POST"])
@login_required
def building_delete(building_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM buildings WHERE id = ?", (building_id,))
        conn.commit()
    flash("Building deleted.", "success")
    return redirect(url_for("content.buildings_list"))


@content_bp.route("/admin/building-floors")
@login_required
def building_floors_list():
    per = 30
    with db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM building_floors").fetchone()[0]
        total_pages = max(1, -(-total // per))
        page = max(1, min(request.args.get("page", 1, type=int), total_pages))
        rows = conn.execute(
            "SELECT * FROM building_floors ORDER BY building, floor_number LIMIT ? OFFSET ?",
            (per, (page - 1) * per),
        ).fetchall()
    return render_template("admin/building_floors.html", floors=rows, page=page, total_pages=total_pages)


@content_bp.route("/admin/building-floors/add", methods=["GET", "POST"])
@login_required
def building_floor_add():
    if request.method == "POST":
        building = request.form["building"]
        with db_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO building_floors
                   (building, floor_number, floor_label, floor_image)
                   VALUES (?, ?, ?, ?)""",
                (
                    building,
                    int(request.form["floor_number"]),
                    request.form["floor_label"],
                    request.form.get("floor_image", ""),
                ),
            )
            slug = _re.sub(r'[^a-z0-9_-]', '_',
                           building.lower().replace("&", "and").replace(" ", "_").replace("/", "_")).strip('_')
            conn.execute(
                """UPDATE campus_pins SET page_url = ?
                   WHERE UPPER(name) = UPPER(?) AND (page_url IS NULL OR page_url = '')""",
                (f"/building/{slug}", building),
            )
            conn.commit()
        flash("Floor saved.", "success")
        return redirect(url_for("content.building_floors_list"))
    return render_template("admin/building_floor_form.html", floor=None, buildings=_get_buildings())


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
            flash("Floor updated.", "success")
            return redirect(url_for("content.building_floors_list"))

    return render_template("admin/building_floor_form.html", floor=floor, buildings=_get_buildings())


@content_bp.route("/admin/building-floors/<int:floor_id>/delete", methods=["POST"])
@login_required
def building_floor_delete(floor_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM building_floors WHERE id = ?", (floor_id,))
        conn.commit()
    return redirect(url_for("content.building_floors_list"))


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

@content_bp.route("/admin/rooms")
@login_required
def rooms_list():
    building_filter = request.args.get("building", "")
    with db_connection() as conn:
        buildings = [r[0] for r in conn.execute(
            "SELECT DISTINCT building FROM rooms ORDER BY building"
        ).fetchall()]
        if building_filter:
            rows = conn.execute(
                "SELECT * FROM rooms WHERE building=? ORDER BY floor, pos_top, pos_left",
                (building_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM rooms ORDER BY building, floor, pos_top, pos_left"
            ).fetchall()
    return render_template("admin/rooms.html", rooms=rows,
                           buildings=buildings, building_filter=building_filter)


@content_bp.route("/admin/rooms/add", methods=["GET", "POST"])
@login_required
def room_add():
    if request.method == "POST":
        with db_connection() as conn:
            conn.execute(
                """INSERT INTO rooms
                   (building, floor, room, description, pos_left, pos_top,
                    pos_width, pos_height, office_key, room_color)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    request.form["building"].strip(),
                    int(request.form.get("floor", 1)),
                    request.form["name"].strip(),
                    request.form.get("desc", "").strip(),
                    float(request.form.get("pos_left", 0)),
                    float(request.form.get("pos_top", 0)),
                    float(request.form.get("pos_width", 10)),
                    float(request.form.get("pos_height", 10)),
                    request.form.get("office_key", "").strip(),
                    _sanitize_room_color(request.form.get("room_color", "")),
                ),
            )
            conn.commit()
        flash("Room added.", "success")
        return redirect(url_for("content.rooms_list"))
    return render_template("admin/room_form.html", room=None, buildings=_get_buildings())


@content_bp.route("/admin/rooms/<int:room_id>/edit", methods=["GET", "POST"])
@login_required
def room_edit(room_id: int):
    with db_connection() as conn:
        room = conn.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
        if room is None:
            abort(404)
        if request.method == "POST":
            conn.execute(
                """UPDATE rooms SET building=?, floor=?, room=?, description=?,
                   pos_left=?, pos_top=?, pos_width=?, pos_height=?,
                   office_key=?, room_color=? WHERE id=?""",
                (
                    request.form["building"].strip(),
                    int(request.form.get("floor", 1)),
                    request.form["name"].strip(),
                    request.form.get("desc", "").strip(),
                    float(request.form.get("pos_left", 0)),
                    float(request.form.get("pos_top", 0)),
                    float(request.form.get("pos_width", 10)),
                    float(request.form.get("pos_height", 10)),
                    request.form.get("office_key", "").strip(),
                    _sanitize_room_color(request.form.get("room_color", "")),
                    room_id,
                ),
            )
            conn.commit()
            flash("Room updated.", "success")
            return redirect(url_for("content.rooms_list",
                                    building=request.form["building"].strip()))
        buildings = _get_buildings()
    return render_template("admin/room_form.html", room=room, buildings=buildings)


@content_bp.route("/admin/rooms/import-csv", methods=["POST"])
@login_required
def rooms_import_csv():
    f = request.files.get("csv_file")
    if not f or not f.filename:
        flash("No file provided.", "error")
        return redirect(url_for("content.rooms_list"))
    _MAX_CSV = 512 * 1024
    data = f.read(_MAX_CSV + 1)
    if len(data) > _MAX_CSV:
        flash("CSV file too large (max 512 KB).", "error")
        return redirect(url_for("content.rooms_list"))
    text = data.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    inserted = skipped = 0
    with db_connection() as conn:
        for i, row in enumerate(reader):
            if i >= 500:
                flash("CSV truncated at 500 rows.", "warning")
                break
            name = row.get("room", "").strip()
            if not name:
                skipped += 1
                continue
            try:
                conn.execute(
                    "INSERT INTO rooms (building, floor, room, description) VALUES (?, ?, ?, ?)",
                    (
                        row.get("building", "").strip(),
                        row.get("floor", "1").strip(),
                        name,
                        row.get("description", "").strip(),
                    ),
                )
                inserted += 1
            except Exception as exc:
                skipped += 1
                current_app.logger.warning("Rooms CSV skip: %s", exc)
        conn.commit()
    flash(
        f"Imported {inserted} room(s)" + (f", skipped {skipped}" if skipped else ""),
        "success",
    )
    return redirect(url_for("content.rooms_list"))


@content_bp.route("/admin/rooms/<int:room_id>/delete", methods=["POST"])
@login_required
def room_delete(room_id: int):
    with db_connection() as conn:
        room = conn.execute("SELECT building FROM rooms WHERE id=?", (room_id,)).fetchone()
        building = room["building"] if room else ""
        conn.execute("DELETE FROM rooms WHERE id=?", (room_id,))
        conn.commit()
    flash("Room deleted.", "success")
    return redirect(url_for("content.rooms_list", building=building))


@content_bp.route("/admin/room-placer", methods=["GET", "POST"])
@login_required
def room_placer():
    building = request.args.get("building", "").strip()
    try:
        floor_num = int(request.args.get("floor", 1))
    except (ValueError, TypeError):
        floor_num = 1

    if request.method == "POST":
        b = request.form.get("building", "").strip()
        f = int(request.form.get("floor", 1))
        with db_connection() as conn:
            conn.execute(
                """INSERT INTO rooms
                   (building, floor, room, description, pos_left, pos_top,
                    pos_width, pos_height, office_key, room_color)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    b, f,
                    request.form.get("name", "").strip(),
                    request.form.get("desc", "").strip(),
                    float(request.form.get("pos_left", 0)),
                    float(request.form.get("pos_top", 0)),
                    float(request.form.get("pos_width", 10)),
                    float(request.form.get("pos_height", 10)),
                    request.form.get("office_key", "").strip(),
                    _sanitize_room_color(request.form.get("room_color", "")),
                ),
            )
            conn.commit()
        flash(f"Room '{request.form.get('name')}' placed.", "success")
        return redirect(url_for("content.room_placer", building=b, floor=f))

    floor_image = None
    placed_rooms = []
    buildings = []
    floor_options = []

    with db_connection() as conn:
        bldg_rows = conn.execute("SELECT name FROM buildings ORDER BY name").fetchall()
        buildings = [r[0] for r in bldg_rows] if bldg_rows else [
            r[0] for r in conn.execute(
                "SELECT DISTINCT building FROM building_floors ORDER BY building"
            ).fetchall()
        ]
        if building:
            bf = conn.execute(
                "SELECT floor_number, floor_label, floor_image FROM building_floors"
                " WHERE building=? ORDER BY floor_number",
                (building,),
            ).fetchall()
            floor_options = [{"number": r["floor_number"], "label": r["floor_label"]} for r in bf]
            row = conn.execute(
                "SELECT floor_image FROM building_floors WHERE building=? AND floor_number=?",
                (building, floor_num),
            ).fetchone()
            if row:
                floor_image = row["floor_image"]
            placed_rooms = conn.execute(
                "SELECT * FROM rooms WHERE building=? AND floor=? ORDER BY pos_top, pos_left",
                (building, floor_num),
            ).fetchall()

    return render_template("admin/room_placer.html",
                           buildings=buildings, building=building,
                           floor_num=floor_num, floor_options=floor_options,
                           floor_image=floor_image, placed_rooms=placed_rooms)


# ---------------------------------------------------------------------------
# Faculty
# ---------------------------------------------------------------------------

@content_bp.route("/admin/faculty")
@login_required
def faculty_list():
    per  = 20
    with db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM faculty").fetchone()[0]
        total_pages = max(1, -(-total // per))
        page = max(1, min(request.args.get("page", 1, type=int), total_pages))
        rows = conn.execute("SELECT * FROM faculty ORDER BY name LIMIT ? OFFSET ?",
                            (per, (page - 1) * per)).fetchall()
    return render_template("admin/faculty_list.html", faculty=rows,
                           page=page, total_pages=total_pages)


@content_bp.route("/admin/faculty/add", methods=["GET", "POST"])
@login_required
def faculty_add():
    if request.method == "POST":
        import json as _json
        schedule = _json.dumps(_parse_schedule_form(request.form))
        with db_connection() as conn:
            conn.execute(
                """INSERT INTO faculty
                   (name, department, position, photo, schedule_image,
                    room, building, office_key, office_position, schedule)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.form["name"],
                    request.form.get("department", ""),
                    request.form.get("position", ""),
                    request.form.get("photo", ""),
                    request.form.get("schedule_image", ""),
                    request.form.get("room", ""),
                    request.form.get("building", ""),
                    request.form.get("office_key", ""),
                    request.form.get("office_position", ""),
                    schedule,
                ),
            )
            conn.commit()
        flash("Faculty member saved.", "success")
        return redirect(url_for("content.faculty_list"))
    return render_template("admin/faculty_form.html", member=None, buildings=_get_buildings())


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
            import json as _json
            schedule = _json.dumps(_parse_schedule_form(request.form))
            conn.execute(
                """UPDATE faculty
                   SET name=?, department=?, position=?, photo=?,
                       schedule_image=?, room=?, building=?, office_key=?,
                       office_position=?, schedule=?
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
                    request.form.get("office_position", ""),
                    schedule,
                    member_id,
                ),
            )
            conn.commit()
            flash("Faculty member updated.", "success")
            return redirect(url_for("content.faculty_list"))

    return render_template("admin/faculty_form.html", member=member, buildings=_get_buildings())


@content_bp.route("/admin/rfid-logs")
@login_required
def rfid_logs():
    per  = 30
    with db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM rfid_logs").fetchone()[0]
        total_pages = max(1, -(-total // per))
        page = max(1, min(request.args.get("page", 1, type=int), total_pages))
        rows = conn.execute(
            "SELECT * FROM rfid_logs ORDER BY id DESC LIMIT ? OFFSET ?",
            (per, (page - 1) * per)
        ).fetchall()
    return render_template("admin/rfid_logs.html", logs=rows,
                           page=page, total_pages=total_pages)


@content_bp.route("/admin/rfid-logs/clear", methods=["POST"])
@login_required
def rfid_logs_clear():
    with db_connection() as conn:
        conn.execute("DELETE FROM rfid_logs")
        conn.commit()
    flash("Scan logs cleared", "success")
    return redirect(url_for("content.rfid_logs"))


@content_bp.route("/admin/rfid-users")
@login_required
def rfid_users_list():
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY name").fetchall()
    return render_template("admin/rfid_users_list.html", users=rows)


@content_bp.route("/admin/rfid-users/new", methods=["GET", "POST"])
@login_required
def rfid_user_add():
    if request.method == "POST":
        uid  = request.form.get("rfid_uid", "").strip()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "student").strip()
        if role not in _VALID_USER_ROLES:
            role = "student"
        if not uid or not name:
            flash("RFID UID and name are required.", "error")
            return render_template("admin/rfid_user_form.html", user=None)
        with db_connection() as conn:
            try:
                conn.execute(
                    "INSERT INTO users (rfid_uid, name, role) VALUES (?,?,?)",
                    (uid, name, role),
                )
                conn.commit()
                flash(f"User '{name}' added.", "success")
            except sqlite3.IntegrityError:
                flash("RFID UID already registered.", "error")
                return render_template("admin/rfid_user_form.html", user=None)
        return redirect(url_for("content.rfid_users_list"))
    return render_template("admin/rfid_user_form.html", user=None)


@content_bp.route("/admin/rfid-users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def rfid_user_edit(user_id: int):
    with db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("content.rfid_users_list"))
    if request.method == "POST":
        uid  = request.form.get("rfid_uid", "").strip()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "student").strip()
        if role not in _VALID_USER_ROLES:
            role = "student"
        if not uid or not name:
            flash("RFID UID and name are required.", "error")
            return render_template("admin/rfid_user_form.html", user=user)
        with db_connection() as conn:
            try:
                conn.execute(
                    "UPDATE users SET rfid_uid=?, name=?, role=? WHERE id=?",
                    (uid, name, role, user_id),
                )
                conn.commit()
                flash(f"User '{name}' updated.", "success")
            except sqlite3.IntegrityError:
                flash("RFID UID already used by another user.", "error")
                return render_template("admin/rfid_user_form.html", user=user)
        return redirect(url_for("content.rfid_users_list"))
    return render_template("admin/rfid_user_form.html", user=user)


@content_bp.route("/admin/rfid-users/<int:user_id>/delete", methods=["POST"])
@login_required
def rfid_user_delete(user_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    flash("User deleted.", "success")
    return redirect(url_for("content.rfid_users_list"))


@content_bp.route("/api/faculty/<int:member_id>/schedule")
def faculty_schedule_api(member_id: int):
    # Kiosk-facing endpoint: visitors are blocked, students/faculty allowed via session role.
    # Admin session also passes (admin has no user_role key, defaults to "visitor" → blocked
    # when accessing kiosk profiles directly, which is fine).
    from flask import session as _session
    if _session.get("user_role", "visitor") == "visitor" and "admin" not in _session:
        return jsonify({"error": "forbidden"}), 403
    with db_connection() as conn:
        row = conn.execute("SELECT schedule FROM faculty WHERE id = ?", (member_id,)).fetchone()
    if row is None:
        return jsonify([])
    try:
        return jsonify(json.loads(row["schedule"] or "[]"))
    except (ValueError, TypeError):
        return jsonify([])


@content_bp.route("/admin/faculty/<int:member_id>/delete", methods=["POST"])
@login_required
def faculty_delete(member_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM faculty WHERE id = ?", (member_id,))
        conn.commit()
    flash("Faculty member deleted.", "success")
    return redirect(url_for("content.faculty_list"))


@content_bp.route("/admin/faculty/import-csv", methods=["POST"])
@login_required
def faculty_import_csv():
    f = request.files.get("csv_file")
    if not f or not f.filename:
        flash("No file provided", "error")
        return redirect(url_for("content.faculty_list"))

    text = f.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    inserted = skipped = 0
    with db_connection() as conn:
        for row in reader:
            try:
                conn.execute(
                    """INSERT INTO faculty
                       (name, department, position, photo, room, building, office_key)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row.get("name", "").strip(),
                        row.get("department", "").strip(),
                        row.get("position", "").strip(),
                        row.get("photo", "").strip(),
                        row.get("room", "").strip(),
                        row.get("building", "").strip(),
                        row.get("office_key", "").strip(),
                    ),
                )
                inserted += 1
            except Exception as exc:
                skipped += 1
                current_app.logger.warning("Faculty CSV skip row %d: %s", inserted + skipped, exc)
        conn.commit()

    msg = f"Imported {inserted} faculty member(s)"
    if skipped:
        msg += f", skipped {skipped} invalid row(s)"
    flash(msg, "success")
    return redirect(url_for("content.faculty_list"))


# ---------------------------------------------------------------------------
# Screensaver image management
# ---------------------------------------------------------------------------

_SCREENSAVER_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "static", "images", "screensaver",
)


@content_bp.route("/admin/screensaver")
@login_required
def screensaver_list():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM screensaver_images ORDER BY display_order, id"
        ).fetchall()
    return render_template("admin/screensaver.html", images=rows)


@content_bp.route("/admin/screensaver/upload", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def screensaver_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        flash("No file provided", "error")
        return redirect(url_for("content.screensaver_list"))
    if _sniff_mime(f.stream) not in _ALLOWED_IMAGE_MIME:
        flash("Only image files allowed", "error")
        return redirect(url_for("content.screensaver_list"))
    os.makedirs(_SCREENSAVER_ROOT, exist_ok=True)
    filename = _safe_filename(f.filename)
    f.save(os.path.join(_SCREENSAVER_ROOT, filename))
    order = int(request.form.get("display_order", 0) or 0)
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO screensaver_images (filename, display_order, active) VALUES (?,?,1)",
            (filename, order),
        )
        conn.commit()
    flash("Image uploaded", "success")
    return redirect(url_for("content.screensaver_list"))


@content_bp.route("/admin/screensaver/<int:image_id>/toggle", methods=["POST"])
@login_required
def screensaver_toggle(image_id: int):
    with db_connection() as conn:
        conn.execute(
            "UPDATE screensaver_images SET active = 1 - active WHERE id = ?",
            (image_id,),
        )
        conn.commit()
    return redirect(url_for("content.screensaver_list"))


@content_bp.route("/admin/screensaver/<int:image_id>/delete", methods=["POST"])
@login_required
def screensaver_delete(image_id: int):
    with db_connection() as conn:
        row = conn.execute(
            "SELECT filename FROM screensaver_images WHERE id = ?", (image_id,)
        ).fetchone()
        if row:
            filepath = os.path.join(_SCREENSAVER_ROOT, row["filename"])
            if os.path.exists(filepath):
                os.remove(filepath)
            conn.execute("DELETE FROM screensaver_images WHERE id = ?", (image_id,))
            conn.commit()
    return redirect(url_for("content.screensaver_list"))


@content_bp.route("/admin/screensaver/<int:image_id>/order", methods=["POST"])
@login_required
def screensaver_order(image_id: int):
    order = int(request.form.get("display_order", 0) or 0)
    with db_connection() as conn:
        conn.execute(
            "UPDATE screensaver_images SET display_order = ? WHERE id = ?",
            (order, image_id),
        )
        conn.commit()
    return redirect(url_for("content.screensaver_list"))


# ---------------------------------------------------------------------------
# About Us admin
# ---------------------------------------------------------------------------

@content_bp.route("/admin/about", methods=["GET", "POST"])
@login_required
def about_admin():
    if request.method == "POST":
        officials_image = request.form.get("officials_image", "").strip()
        with db_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO about_settings (key, value) VALUES ('officials_image', ?)",
                (officials_image,),
            )
            conn.commit()
        flash("Saved.", "success")
        return redirect(url_for("content.about_admin"))
    with db_connection() as conn:
        row = conn.execute(
            "SELECT value FROM about_settings WHERE key='officials_image'"
        ).fetchone()
        researchers = conn.execute(
            "SELECT * FROM about_researchers ORDER BY sort_order, id"
        ).fetchall()
    officials_image = row["value"] if row else ""
    return render_template("admin/about.html",
                           officials_image=officials_image,
                           researchers=[dict(r) for r in researchers])


@content_bp.route("/admin/about/researcher/add", methods=["POST"])
@login_required
def about_researcher_add():
    name = request.form.get("name", "").strip()[:200]
    photo = request.form.get("photo", "").strip()
    order = request.form.get("sort_order", 0, type=int)
    if name:
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO about_researchers (name, photo, sort_order) VALUES (?, ?, ?)",
                (name, photo, order),
            )
            conn.commit()
    return redirect(url_for("content.about_admin"))


@content_bp.route("/admin/about/researcher/<int:rid>/edit", methods=["POST"])
@login_required
def about_researcher_edit(rid: int):
    name = request.form.get("name", "").strip()[:200]
    photo = request.form.get("photo", "").strip()
    order = request.form.get("sort_order", 0, type=int)
    if name:
        with db_connection() as conn:
            conn.execute(
                "UPDATE about_researchers SET name=?, photo=?, sort_order=? WHERE id=?",
                (name, photo, order, rid),
            )
            conn.commit()
    return redirect(url_for("content.about_admin"))


@content_bp.route("/admin/about/researcher/<int:rid>/delete", methods=["POST"])
@login_required
def about_researcher_delete(rid: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM about_researchers WHERE id=?", (rid,))
        conn.commit()
    return redirect(url_for("content.about_admin"))


@content_bp.route("/api/screensaver-images")
def api_screensaver_images():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT filename FROM screensaver_images WHERE active = 1 ORDER BY display_order, id"
        ).fetchall()
    return jsonify([r["filename"] for r in rows])


# ── Campus Map Image ─────────────────────────────────────────────────────────

@content_bp.route("/admin/campus-map", methods=["GET", "POST"])
@login_required
def campus_map_admin():
    _MAP_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "static", "images", "labeled_map.jpg",
    )
    error = None
    if request.method == "POST":
        f = request.files.get("campus_map")
        if not f or not f.filename:
            error = "No file selected."
        else:
            mime = _sniff_mime(f.stream)
            if mime not in _ALLOWED_IMAGE_MIME:
                error = "Only image files are allowed (JPEG, PNG, WebP, GIF)."
            else:
                data = f.read()
                if len(data) > _MAX_IMAGE_BYTES:
                    error = "Image exceeds 5 MB limit."
                else:
                    os.makedirs(os.path.dirname(_MAP_PATH), exist_ok=True)
                    with open(_MAP_PATH, "wb") as fh:
                        fh.write(data)
                    flash("Campus map updated.", "success")
                    return redirect(url_for("content.campus_map_admin"))
    exists = os.path.isfile(_MAP_PATH)
    return render_template("admin/campus_map.html", exists=exists, error=error)


# ── Campus Pins ──────────────────────────────────────────────────────────────

@content_bp.route("/admin/campus-pins")
@login_required
def campus_pins_list():
    with db_connection() as conn:
        pins = conn.execute(
            "SELECT * FROM campus_pins ORDER BY CAST(number AS INTEGER), number, id"
        ).fetchall()
    return render_template("admin/campus_pins.html", pins=[dict(p) for p in pins])


@content_bp.route("/admin/campus-pins/placer", methods=["GET", "POST"])
@login_required
def campus_pins_placer():
    if request.method == "POST":
        number = request.form.get("number", "").strip()[:10] or None
        name = request.form.get("name", "").strip()[:200]
        page_url = request.form.get("page_url", "").strip()[:200] or None
        left_pct = request.form.get("left_pct", type=float)
        top_pct = request.form.get("top_pct", type=float)
        if (name
                and left_pct is not None and 0.0 <= left_pct <= 100.0
                and top_pct is not None and 0.0 <= top_pct <= 100.0):
            with db_connection() as conn:
                conn.execute(
                    "INSERT INTO campus_pins (number, name, left_pct, top_pct, page_url) VALUES (?, ?, ?, ?, ?)",
                    (number, name, left_pct, top_pct, page_url),
                )
                conn.commit()
        return redirect(url_for("content.campus_pins_placer"))
    with db_connection() as conn:
        pins = conn.execute(
            "SELECT * FROM campus_pins ORDER BY CAST(number AS INTEGER), number, id"
        ).fetchall()
    return render_template("admin/campus_placer.html", pins=[dict(p) for p in pins])


@content_bp.route("/admin/campus-pins/<int:pin_id>/edit", methods=["GET", "POST"])
@login_required
def campus_pin_edit(pin_id: int):
    with db_connection() as conn:
        pin = conn.execute("SELECT * FROM campus_pins WHERE id=?", (pin_id,)).fetchone()
    if pin is None:
        abort(404)
    if request.method == "POST":
        number = request.form.get("number", "").strip()[:10] or None
        name = request.form.get("name", "").strip()[:200]
        page_url = request.form.get("page_url", "").strip()[:200] or None
        directions_text = request.form.get("directions_text", "").strip()[:1000] or None
        photo_raw = request.form.get("photo", "").strip()
        photo = photo_raw if photo_raw and _SAFE_IMAGE_PATH_RE.fullmatch(photo_raw) else None
        left_pct = request.form.get("left_pct", type=float)
        top_pct = request.form.get("top_pct", type=float)
        if name and left_pct is not None and top_pct is not None:
            with db_connection() as conn:
                conn.execute(
                    "UPDATE campus_pins SET number=?, name=?, left_pct=?, top_pct=?, page_url=?, directions_text=?, photo=? WHERE id=?",
                    (number, name, left_pct, top_pct, page_url, directions_text, photo, pin_id),
                )
                conn.commit()
        return redirect(url_for("content.campus_pins_list"))
    return render_template("admin/campus_pin_form.html", pin=dict(pin))


@content_bp.route("/admin/campus-pins/<int:pin_id>/delete", methods=["POST"])
@login_required
def campus_pin_delete(pin_id: int):
    next_url = request.form.get("next", "list")
    with db_connection() as conn:
        conn.execute("DELETE FROM campus_pins WHERE id=?", (pin_id,))
        conn.commit()
    if next_url == "placer":
        return redirect(url_for("content.campus_pins_placer"))
    return redirect(url_for("content.campus_pins_list"))


@content_bp.route("/api/campus-pins")
@limiter.limit("60/minute")
def api_campus_pins():
    with db_connection() as conn:
        pins = conn.execute(
            """SELECT cp.id, cp.number, cp.name, cp.left_pct, cp.top_pct,
                      cp.page_url, cp.directions_text,
                      COALESCE(cp.photo, b.image) AS photo
               FROM campus_pins cp
               LEFT JOIN buildings b ON LOWER(b.name) = LOWER(cp.name)
               ORDER BY CAST(cp.number AS INTEGER), cp.number, cp.id"""
        ).fetchall()
    return jsonify([dict(p) for p in pins])


@content_bp.route("/api/offices")
@limiter.limit("60/minute")
def api_offices_public():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT key, name, building_url, location FROM offices WHERE building_url IS NOT NULL AND building_url != '' ORDER BY name"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Campus path editor
# ---------------------------------------------------------------------------

@content_bp.route("/admin/campus-paths")
@login_required
def campus_path_editor():
    with db_connection() as conn:
        nodes = conn.execute("SELECT * FROM campus_nodes ORDER BY id").fetchall()
        edges = conn.execute(
            "SELECT ce.id, ce.node_a, ce.node_b, na.label AS label_a, nb.label AS label_b "
            "FROM campus_edges ce "
            "JOIN campus_nodes na ON na.id = ce.node_a "
            "JOIN campus_nodes nb ON nb.id = ce.node_b "
            "ORDER BY ce.id"
        ).fetchall()
    nodes_list = [dict(n) for n in nodes]
    nodes_by_id = {n["id"]: n for n in nodes_list}
    return render_template("admin/campus_path_editor.html",
                           nodes=nodes_list,
                           edges=[dict(e) for e in edges],
                           nodes_by_id=nodes_by_id)


@content_bp.route("/admin/campus-paths/nodes", methods=["POST"])
@login_required
def campus_path_node_add():
    label = request.form.get("label", "").strip()[:100]
    x_pct = request.form.get("x_pct", type=float)
    y_pct = request.form.get("y_pct", type=float)
    if x_pct is not None and y_pct is not None:
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO campus_nodes (label, x_pct, y_pct) VALUES (?, ?, ?)",
                (label, x_pct, y_pct),
            )
            conn.commit()
    return redirect(url_for("content.campus_path_editor"))


@content_bp.route("/admin/campus-paths/nodes/<int:node_id>/delete", methods=["POST"])
@login_required
def campus_path_node_delete(node_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM campus_edges WHERE node_a=? OR node_b=?", (node_id, node_id))
        conn.execute("DELETE FROM campus_nodes WHERE id=?", (node_id,))
        conn.commit()
    return redirect(url_for("content.campus_path_editor"))


@content_bp.route("/admin/campus-paths/edges", methods=["POST"])
@login_required
def campus_path_edge_add():
    node_a = request.form.get("node_a", type=int)
    node_b = request.form.get("node_b", type=int)
    if node_a and node_b and node_a != node_b:
        with db_connection() as conn:
            exists = conn.execute(
                "SELECT id FROM campus_edges WHERE (node_a=? AND node_b=?) OR (node_a=? AND node_b=?)",
                (node_a, node_b, node_b, node_a),
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO campus_edges (node_a, node_b) VALUES (?, ?)", (node_a, node_b)
                )
                conn.commit()
    return redirect(url_for("content.campus_path_editor"))


@content_bp.route("/admin/campus-paths/edges/<int:edge_id>/delete", methods=["POST"])
@login_required
def campus_path_edge_delete(edge_id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM campus_edges WHERE id=?", (edge_id,))
        conn.commit()
    return redirect(url_for("content.campus_path_editor"))


@content_bp.route("/api/campus-paths")
@limiter.limit("60/minute")
def api_campus_paths():
    with db_connection() as conn:
        nodes = conn.execute("SELECT id, label, x_pct, y_pct FROM campus_nodes ORDER BY id").fetchall()
        edges = conn.execute("SELECT id, node_a, node_b FROM campus_edges ORDER BY id").fetchall()
    return jsonify({"nodes": [dict(n) for n in nodes], "edges": [dict(e) for e in edges]})


# ---------------------------------------------------------------------------
# Floor path editor
# ---------------------------------------------------------------------------

@content_bp.route("/admin/floor-paths")
@login_required
def floor_path_editor():
    building = request.args.get("building", "")
    floor = request.args.get("floor", "")
    with db_connection() as conn:
        buildings = conn.execute(
            "SELECT DISTINCT building FROM building_floors ORDER BY building"
        ).fetchall()
        floors = []
        floor_image = None
        nodes = []
        edges = []
        if building:
            floors = conn.execute(
                "SELECT floor_number, floor_label FROM building_floors WHERE building=? ORDER BY floor_number",
                (building,),
            ).fetchall()
        rooms = []
        if building and floor:
            row = conn.execute(
                "SELECT floor_image FROM building_floors WHERE building=? AND floor_number=?",
                (building, floor),
            ).fetchone()
            floor_image = row["floor_image"] if row else None
            rooms = conn.execute(
                "SELECT room, pos_left, pos_top, pos_width, pos_height FROM rooms "
                "WHERE building=? AND floor=? ORDER BY pos_top, pos_left",
                (building, floor),
            ).fetchall()
            nodes = conn.execute(
                "SELECT * FROM floor_nodes WHERE building=? AND floor=? ORDER BY id",
                (building, floor),
            ).fetchall()
            edges = conn.execute(
                "SELECT fe.id, fe.from_id, fe.to_id, na.label AS label_a, nb.label AS label_b "
                "FROM floor_edges fe "
                "JOIN floor_nodes na ON na.id = fe.from_id "
                "JOIN floor_nodes nb ON nb.id = fe.to_id "
                "WHERE na.building=? AND na.floor=? "
                "ORDER BY fe.id",
                (building, floor),
            ).fetchall()
    nodes_list = [dict(n) for n in nodes]
    nodes_by_id = {n["id"]: n for n in nodes_list}
    return render_template("admin/floor_path_editor.html",
                           buildings=[dict(b) for b in buildings],
                           floors=[dict(f) for f in floors],
                           floor_image=floor_image,
                           nodes=nodes_list,
                           edges=[dict(e) for e in edges],
                           nodes_by_id=nodes_by_id,
                           rooms=[dict(r) for r in rooms],
                           selected_building=building,
                           selected_floor=floor)


@content_bp.route("/admin/floor-paths/nodes", methods=["POST"])
@login_required
def floor_path_node_add():
    building = request.form.get("building", "").strip()[:200]
    floor = request.form.get("floor", "").strip()[:20]
    label = request.form.get("label", "").strip()[:100]
    x_pct = request.form.get("x_pct", type=float)
    y_pct = request.form.get("y_pct", type=float)
    if building and floor and x_pct is not None and y_pct is not None:
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO floor_nodes (building, floor, label, x_pct, y_pct) VALUES (?, ?, ?, ?, ?)",
                (building, floor, label or None, x_pct, y_pct),
            )
            conn.commit()
    return redirect(url_for("content.floor_path_editor", building=building, floor=floor))


@content_bp.route("/admin/floor-paths/nodes/<int:node_id>/delete", methods=["POST"])
@login_required
def floor_path_node_delete(node_id: int):
    with db_connection() as conn:
        node = conn.execute("SELECT building, floor FROM floor_nodes WHERE id=?", (node_id,)).fetchone()
        building = node["building"] if node else ""
        floor = node["floor"] if node else ""
        conn.execute("DELETE FROM floor_edges WHERE from_id=? OR to_id=?", (node_id, node_id))
        conn.execute("DELETE FROM floor_nodes WHERE id=?", (node_id,))
        conn.commit()
    return redirect(url_for("content.floor_path_editor", building=building, floor=floor))


@content_bp.route("/admin/floor-paths/edges", methods=["POST"])
@login_required
def floor_path_edge_add():
    from_id = request.form.get("from_id", type=int)
    to_id = request.form.get("to_id", type=int)
    building = request.form.get("building", "")
    floor = request.form.get("floor", "")
    if from_id and to_id and from_id != to_id:
        with db_connection() as conn:
            from_node = conn.execute(
                "SELECT id FROM floor_nodes WHERE id=? AND building=? AND floor=?",
                (from_id, building, floor),
            ).fetchone()
            to_node = conn.execute(
                "SELECT id FROM floor_nodes WHERE id=? AND building=? AND floor=?",
                (to_id, building, floor),
            ).fetchone()
            if from_node and to_node:
                exists = conn.execute(
                    "SELECT id FROM floor_edges WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)",
                    (from_id, to_id, to_id, from_id),
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO floor_edges (from_id, to_id) VALUES (?, ?)", (from_id, to_id)
                    )
                    conn.commit()
    return redirect(url_for("content.floor_path_editor", building=building, floor=floor))


@content_bp.route("/admin/floor-paths/edges/<int:edge_id>/delete", methods=["POST"])
@login_required
def floor_path_edge_delete(edge_id: int):
    building = request.form.get("building", "")
    floor = request.form.get("floor", "")
    with db_connection() as conn:
        conn.execute("DELETE FROM floor_edges WHERE id=?", (edge_id,))
        conn.commit()
    return redirect(url_for("content.floor_path_editor", building=building, floor=floor))


@content_bp.route("/api/floor-paths")
@limiter.limit("60/minute")
def api_floor_paths():
    building = request.args.get("building", "")
    floor = request.args.get("floor", "")
    if not building or not floor:
        return jsonify({"nodes": [], "edges": []})
    with db_connection() as conn:
        nodes = conn.execute(
            "SELECT id, label, x_pct, y_pct FROM floor_nodes WHERE building=? AND floor=? ORDER BY id",
            (building, floor),
        ).fetchall()
        edges = conn.execute(
            "SELECT fe.id, fe.from_id, fe.to_id FROM floor_edges fe "
            "JOIN floor_nodes fn_from ON fn_from.id = fe.from_id "
            "JOIN floor_nodes fn_to   ON fn_to.id   = fe.to_id "
            "WHERE fn_from.building=? AND fn_from.floor=? "
            "  AND fn_to.building=?   AND fn_to.floor=? "
            "ORDER BY fe.id",
            (building, floor, building, floor),
        ).fetchall() if nodes else []
    return jsonify({"nodes": [dict(n) for n in nodes], "edges": [dict(e) for e in edges]})


@content_bp.route("/api/building-floors")
@limiter.limit("60/minute")
def api_building_floors():
    building = request.args.get("building", "").strip()
    if not building:
        return jsonify([])
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT floor_number, floor_label, floor_image FROM building_floors"
            " WHERE building=? ORDER BY floor_number",
            (building,),
        ).fetchall()
    import posixpath as _pp, time as _time
    def _safe_img(img):
        if not img:
            return None
        clean = _pp.normpath(img.replace("\\", "/")).lstrip("/.")
        if not clean or clean.startswith(".."):
            return None
        abs_path = os.path.join(_STATIC_ROOT, clean)
        mtime = int(os.path.getmtime(abs_path)) if os.path.exists(abs_path) else int(_time.time())
        return "/static/" + clean + "?v=" + str(mtime)

    return jsonify([
        {
            "floor_number": r["floor_number"],
            "floor_label": r["floor_label"],
            "floor_image_url": _safe_img(r["floor_image"]),
        }
        for r in rows
    ])



@content_bp.route("/api/kiosk-settings")
@limiter.limit("60/minute")
def api_kiosk_settings():
    try:
        with db_connection() as conn:
            rows = conn.execute("SELECT key, value FROM kiosk_settings").fetchall()
        return jsonify({r["key"]: r["value"] for r in rows})
    except Exception:
        return jsonify({})
