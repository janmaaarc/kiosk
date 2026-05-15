import io
import os
from urllib.parse import quote

import qrcode
from flask import Blueprint, Response, jsonify, redirect, render_template, request, send_file, session

from kiosk_app.db import db_connection
from kiosk_app.extensions import csrf, limiter

main_bp = Blueprint("main", __name__)

_VALID_ROLES = frozenset({"student", "faculty", "visitor"})
_LOCAL_ADDRS = frozenset({"127.0.0.1", "::1", "localhost"})


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/menu")
def menu():
    return render_template("menu.html",
                           user_name=session.get("user_name"),
                           user_role=session.get("user_role", "visitor"))


@main_bp.route("/faculty")
def faculty():
    role = session.get("user_role", "visitor")
    with db_connection() as conn:
        rows = conn.execute("""
            SELECT f.*, o.name AS office_name
            FROM faculty f
            LEFT JOIN offices o ON COALESCE(f.office_key, '') = o.key
            ORDER BY f.name
        """).fetchall()
    return render_template("faculty.html",
                           faculty_list=[dict(r) for r in rows],
                           show_schedule=(role != "visitor"))


def _log_rfid(conn, uid: str, name: str, role: str) -> None:
    from datetime import datetime
    conn.execute(
        "INSERT INTO rfid_logs (rfid_uid, name, role, scanned_at) VALUES (?,?,?,?)",
        (uid, name, role, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()


@main_bp.route("/rfid")
@limiter.limit("30 per minute")
def rfid():
    if request.remote_addr not in _LOCAL_ADDRS:
        return redirect("/menu")
    uid = request.args.get("uid", "").strip()
    if not uid:
        return redirect("/menu")
    with db_connection() as conn:
        row = conn.execute(
            "SELECT name, role FROM users WHERE rfid_uid = ?", (uid,)
        ).fetchone()
        if row:
            role = row["role"] if row["role"] in _VALID_ROLES else "visitor"
            _log_rfid(conn, uid, row["name"], role)
            session["user_role"] = role
            session["user_name"] = row["name"]
            return render_template("rfid_scan.html",
                                   user_name=row["name"], user_role=role)
        else:
            _log_rfid(conn, uid, "Unknown", "unregistered")
            session.clear()
    return render_template("rfid_scan.html", user_name=None, user_role="unregistered")


@main_bp.route("/check_rfid", methods=["POST"])
@csrf.exempt
@limiter.limit("60 per minute")
def check_rfid():
    if request.remote_addr not in _LOCAL_ADDRS:
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
            _log_rfid(conn, uid, row["name"], row["role"])
            session["user_role"] = row["role"]
            session["user_name"] = row["name"]
            return jsonify({"status": "authorized",
                            "user": {"name": row["name"], "role": row["role"]}})
        else:
            _log_rfid(conn, uid, "Unknown", "unregistered")
            session.clear()
            return jsonify({"status": "unauthorized",
                            "message": "RFID not registered"})


@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@main_bp.route("/profile")
def profile():
    role = session.get("user_role", "visitor")
    return render_template("profile.html", show_schedule=(role != "visitor"))


@main_bp.route("/about")
def about():
    with db_connection() as conn:
        researchers = conn.execute(
            "SELECT * FROM about_researchers ORDER BY sort_order, id"
        ).fetchall()
        row = conn.execute(
            "SELECT value FROM about_settings WHERE key='officials_image'"
        ).fetchone()
    officials_image = row["value"] if row else None
    return render_template("about.html",
                           researchers=[dict(r) for r in researchers],
                           officials_image=officials_image)



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
            "SELECT room, building, floor FROM rooms WHERE room LIKE ? ESCAPE '\\' LIMIT 5",
            (pattern,),
        ).fetchall():
            building = row["building"] or ""
            floor = row["floor"] or 1
            pin = conn.execute(
                "SELECT page_url FROM campus_pins WHERE LOWER(name) LIKE LOWER(?)",
                ("%" + building + "%",),
            ).fetchone()
            page_url = pin["page_url"] if pin else None
            if page_url:
                url = page_url + "?floor=" + str(floor) + "&location=" + quote(row["room"], safe="")
            else:
                url = None
            results.append({"type": "room", "name": row["room"],
                            "building": building,
                            "floor": floor,
                            "url": url})

        raw_role = session.get("user_role", "visitor")
        role = raw_role if raw_role in _VALID_ROLES else "visitor"
        role_pattern = f"%,{role},%"
        for row in conn.execute(
            "SELECT key, name FROM offices WHERE name LIKE ? ESCAPE '\\'"
            " AND (expires_at IS NULL OR expires_at > datetime('now'))"
            " AND (visible_to IS NULL OR visible_to LIKE ?) LIMIT 5",
            (pattern, role_pattern),
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

        try:
            conn.execute("INSERT INTO search_logs (query) VALUES (?)", (q,))
            conn.commit()
        except Exception:
            pass

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


def _is_local_url(url: str) -> bool:
    from urllib.parse import urlparse
    if not url.startswith("http"):
        return True  # bare path is fine
    host = urlparse(url).hostname or ""
    return (
        host in ("localhost", "127.0.0.1")
        or host.startswith("192.168.")
        or host.startswith("10.")
        or (host.startswith("172.") and 16 <= int(host.split(".")[1]) <= 31)
    )


@main_bp.route("/qr")
@limiter.limit("60 per minute")
def qr_code():
    data = request.args.get("data", "").strip()
    if not data:
        return ("missing data", 400)
    if not _is_local_url(data):
        return ("only local URLs allowed", 403)
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
    except Exception as exc:
        from flask import current_app
        current_app.logger.error("healthz DB check failed: %s", exc)
        return jsonify({"status": "degraded"}), 503


@main_bp.route("/api/departments")
def api_departments():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT department FROM faculty WHERE department IS NOT NULL AND department != '' ORDER BY department"
        ).fetchall()
    depts = [r["department"] for r in rows]
    return jsonify(depts)
