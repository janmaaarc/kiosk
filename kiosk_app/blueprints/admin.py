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

        if len(password) > 72:
            return render_template("admin_login.html")

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
        flash("Invalid username or password.", "error")

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

