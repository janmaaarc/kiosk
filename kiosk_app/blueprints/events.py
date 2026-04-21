from flask import Blueprint, render_template

from kiosk_app.data.events import EVENT_DETAILS, EVENTS_LIST

events_bp = Blueprint("events", __name__)


@events_bp.route("/events")
def events():
    return render_template("events.html", events=EVENTS_LIST)


@events_bp.route("/event/<int:event_id>")
def event_detail(event_id: int):
    event = EVENT_DETAILS.get(event_id)
    return render_template("event_detail.html", event=event)
