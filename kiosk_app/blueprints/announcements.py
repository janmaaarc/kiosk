from flask import Blueprint, abort, render_template, request

from kiosk_app.data.announcements import ANNOUNCEMENTS

announcements_bp = Blueprint("announcements", __name__)

_ALLOWED_FILES = {a["file"] for a in ANNOUNCEMENTS}


@announcements_bp.route("/announcements")
def digital_announcements():
    return render_template("digital_announcements.html", announcements=ANNOUNCEMENTS)


@announcements_bp.route("/announcement-view")
def announcement_view():
    file = request.args.get("file", "")
    if file not in _ALLOWED_FILES:
        abort(400)
    return render_template("announcement_view.html", file=file)
