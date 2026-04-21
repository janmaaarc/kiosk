from flask import Blueprint, render_template, request

from kiosk_app.data.offices import OFFICE_DETAILS, OFFICE_SUMMARIES

offices_bp = Blueprint("offices", __name__)


@offices_bp.route("/office-selection")
def office_selection():
    return render_template("office_selection.html", offices=OFFICE_SUMMARIES)


@offices_bp.route("/office")
def office():
    office_name = request.args.get("name", "Registrar")
    selected = next(
        (o for o in OFFICE_DETAILS if o["key"] == office_name),
        OFFICE_DETAILS[0],
    )
    return render_template("office.html", offices=OFFICE_DETAILS, selected=selected)
