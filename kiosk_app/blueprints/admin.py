import csv
import io

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

        with db_connection() as conn:
            user = conn.execute(
                "SELECT password_hash FROM admins WHERE username=?",
                (username,),
            ).fetchone()

        if user and bcrypt.check_password_hash(user[0], password):
            session.clear()
            session["admin"] = username
            current_app.logger.info("admin login ok: user=%s ip=%s", username, request.remote_addr)
            return redirect(url_for("admin.dashboard"))

        current_app.logger.warning("admin login failed: user=%s ip=%s", username, request.remote_addr)

    return render_template("admin_login.html")


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin.admin_login"))


@admin_bp.route("/rooms")
@login_required
def rooms():
    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM rooms").fetchall()
    return render_template("rooms.html", rooms=rows)


@admin_bp.route("/add_room", methods=["GET", "POST"])
@login_required
def add_room():
    if request.method == "POST":
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO rooms (building, floor, room, description,"
                " pos_left, pos_top, pos_width, pos_height, office_key, room_color)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    request.form["building"],
                    request.form["floor"],
                    request.form["room"],
                    request.form["description"],
                    int(request.form.get("pos_left", 0)),
                    int(request.form.get("pos_top", 0)),
                    int(request.form.get("pos_width", 10)),
                    int(request.form.get("pos_height", 10)),
                    request.form.get("office_key", ""),
                    request.form.get("room_color", ""),
                ),
            )
            conn.commit()

        return redirect(url_for("admin.rooms"))

    return render_template("add_room.html")


@admin_bp.route("/edit_room/<int:room_id>", methods=["GET", "POST"])
@login_required
def edit_room(room_id: int):
    with db_connection() as conn:
        room = conn.execute(
            "SELECT * FROM rooms WHERE id = ?", (room_id,)
        ).fetchone()

        if room is None:
            abort(404)

        if request.method == "POST":
            conn.execute(
                "UPDATE rooms SET building=?, floor=?, room=?, description=?,"
                " pos_left=?, pos_top=?, pos_width=?, pos_height=?,"
                " office_key=?, room_color=? WHERE id=?",
                (
                    request.form["building"],
                    request.form["floor"],
                    request.form["room"],
                    request.form["description"],
                    int(request.form.get("pos_left", 0)),
                    int(request.form.get("pos_top", 0)),
                    int(request.form.get("pos_width", 10)),
                    int(request.form.get("pos_height", 10)),
                    request.form.get("office_key", ""),
                    request.form.get("room_color", ""),
                    room_id,
                ),
            )
            conn.commit()
            return redirect(url_for("admin.rooms"))

    return render_template("edit_room.html", room=room)


@admin_bp.route("/delete_room/<int:id>", methods=["POST"])
@login_required
def delete_room(id: int):
    with db_connection() as conn:
        conn.execute("DELETE FROM rooms WHERE id = ?", (id,))
        conn.commit()
    return redirect(url_for("admin.rooms"))


@admin_bp.route("/rooms/import-csv", methods=["POST"])
@login_required
def rooms_import_csv():
    f = request.files.get("csv_file")
    if not f or not f.filename:
        flash("No file provided", "error")
        return redirect(url_for("admin.rooms"))

    text = f.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    inserted = 0
    skipped = 0
    with db_connection() as conn:
        for row in reader:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO rooms"
                    " (building, floor, room, description,"
                    " pos_left, pos_top, pos_width, pos_height, office_key)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        row.get("building", ""),
                        row.get("floor", ""),
                        row.get("room", ""),
                        row.get("description", ""),
                        int(row.get("pos_left", 0) or 0),
                        int(row.get("pos_top", 0) or 0),
                        int(row.get("pos_width", 10) or 10),
                        int(row.get("pos_height", 10) or 10),
                        row.get("office_key", ""),
                    ),
                )
                inserted += 1
            except Exception as exc:
                skipped += 1
                current_app.logger.warning("CSV import skipped row %s: %s", row, exc)
        conn.commit()

    msg = f"Imported {inserted} room(s)"
    if skipped:
        msg += f", skipped {skipped} invalid row(s)"
    flash(msg, "success")
    return redirect(url_for("admin.rooms"))

