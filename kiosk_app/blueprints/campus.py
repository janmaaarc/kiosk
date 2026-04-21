from flask import Blueprint, render_template, request

from kiosk_app.db import db_connection

campus_bp = Blueprint("campus", __name__)


@campus_bp.route("/campus")
def campus():
    with db_connection() as conn:
        rows = conn.execute("SELECT DISTINCT building FROM rooms").fetchall()
    buildings = [row[0] for row in rows]

    return render_template("campus.html", buildings=buildings)


@campus_bp.route("/campus_map")
def campus_map():
    return render_template("campus.html")


@campus_bp.route("/campus/<building_name>")
def building(building_name: str):
    with db_connection() as conn:
        floors = conn.execute(
            "SELECT DISTINCT floor FROM rooms WHERE LOWER(building) = LOWER(?)",
            (building_name,),
        ).fetchall()

    return render_template("building.html", building=building_name, floors=floors)


@campus_bp.route("/floor/<building_name>/<floor_number>")
def floor(building_name: str, floor_number: str):
    with db_connection() as conn:
        rooms = conn.execute(
            "SELECT room FROM rooms WHERE LOWER(building) = LOWER(?) AND floor = ?",
            (building_name, floor_number),
        ).fetchall()

    highlight = request.args.get("highlight")
    directions = (
        f"Proceed to {highlight} on floor {floor_number} of {building_name}."
        if highlight
        else None
    )

    return render_template(
        "floor.html",
        building=building_name,
        floor=floor_number,
        rooms=rooms,
        highlight=highlight,
        directions=directions,
    )


@campus_bp.route("/campus/<building_name>/<floor_number>/<room_name>")
def room(building_name: str, floor_number: str, room_name: str):
    return render_template(
        "room.html",
        building=building_name,
        floor=floor_number,
        room=room_name,
    )


@campus_bp.route("/building_navigation")
def building_navigation():
    room_param = request.args.get("room")
    return render_template("building_navigation.html", room=room_param)


@campus_bp.route("/room_navigation")
def room_navigation():
    return render_template("room_navigation.html")


def _building(name, floors=3):
    return render_template("building_detail.html", building_name=name,
                           floors=range(floors))


@campus_bp.route("/ylagan_hall")
def ylagan():
    return _building("Ylagan Hall", floors=2)


@campus_bp.route("/automotive_building")
def automotive():
    return _building("Automotive Building")


@campus_bp.route("/academic_building")
def academic_building():
    return render_template("academic.html")


@campus_bp.route("/waf_&_rac_building")
def waf_rac_building():
    return _building("WAF & RAC Building")


@campus_bp.route("/new_admin_building")
def new_admin_building():
    return _building("New Admin Building", floors=4)


@campus_bp.route("/old_admin_building")
def old_admin_building():
    return _building("Old Admin Building", floors=2)


@campus_bp.route("/fsm_building")
def fsm_building():
    return _building("FSM Building")


@campus_bp.route("/civil_tech_building")
def civil_tech_building():
    return _building("Civil Tech Building")


@campus_bp.route("/waf_&_fsm_building")
def waf_fsm_building():
    return _building("WAF & FSM Building")


@campus_bp.route("/tech_building")
def tech_building():
    return _building("Tech Building", floors=4)


@campus_bp.route("/graduate_school_building")
def graduate_school_building():
    return _building("Graduate School Building", floors=2)


@campus_bp.route("/mechanical_building")
def mechanical_building():
    return _building("Mechanical Building")


@campus_bp.route("/te_building")
def te_building():
    return _building("TE Building")


@campus_bp.route("/it_building")
def it_building():
    return render_template("it_building.html")


@campus_bp.route("/engineering-floor1")
def engineering_floor1():
    return _building("Engineering Building", floors=1)
