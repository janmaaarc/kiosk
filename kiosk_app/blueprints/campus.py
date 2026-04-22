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


def _floor_plan(building_name: str, floor_count: int = 3, base_url: str = "",
                custom_floors: dict | None = None):
    """Generic floor_plan.html renderer for any building."""
    try:
        floor_number = int(request.args.get("floor", 1))
    except (ValueError, TypeError):
        floor_number = 1

    if custom_floors is not None:
        floors = custom_floors
    else:
        with db_connection() as conn:
            bf_rows = conn.execute(
                "SELECT floor_number, floor_label, floor_image FROM building_floors"
                " WHERE building = ? ORDER BY floor_number",
                (building_name,),
            ).fetchall()

            if bf_rows:
                rm_rows = conn.execute(
                    "SELECT room, description, pos_left, pos_top, pos_width,"
                    " pos_height, office_key, floor FROM rooms"
                    " WHERE LOWER(building)=LOWER(?)",
                    (building_name,),
                ).fetchall()

                rooms_by_floor: dict = {}
                for rm in rm_rows:
                    rooms_by_floor.setdefault(str(rm["floor"]), []).append({
                        "name": rm["room"],
                        "desc": rm["description"] or "",
                        "left": rm["pos_left"],
                        "top": rm["pos_top"],
                        "width": rm["pos_width"],
                        "height": rm["pos_height"],
                        "office_key": rm["office_key"] or "",
                    })

                floors = {
                    r["floor_number"]: {
                        "label": r["floor_label"],
                        "image": r["floor_image"],
                        "rooms": rooms_by_floor.get(str(r["floor_number"]), []),
                    }
                    for r in bf_rows
                }
            else:
                floors = {
                    n: {
                        "label": "Ground Floor" if n == 1 else f"Floor {n}",
                        "image": None,
                        "rooms": [],
                    }
                    for n in range(1, floor_count + 1)
                }

    if floor_number not in floors:
        floor_number = min(floors)

    floor_data = floors[floor_number]
    highlight = request.args.get("location")

    return render_template(
        "floor_plan.html",
        building_name=building_name,
        floor_number=floor_number,
        floor_label=floor_data["label"],
        floor_image=floor_data.get("image"),
        rooms=floor_data.get("rooms", []),
        all_floors=[
            {"number": n, "label": f["label"], "url": f"/{base_url}?floor={n}"}
            for n, f in floors.items()
        ],
        highlight=highlight,
    )


@campus_bp.route("/rodriguez_building")
def rodriguez_building():
    return _floor_plan("Rodriguez Building", floor_count=3, base_url="rodriguez_building")


@campus_bp.route("/mist_ncestd_dorm")
def mist_ncestd_dorm():
    return _floor_plan("MIST-NCESTD Dorm", floor_count=4, base_url="mist_ncestd_dorm")


@campus_bp.route("/mist_ncestd_building")
def mist_ncestd_building():
    return _floor_plan("MIST-NCESTD Building", floor_count=3, base_url="mist_ncestd_building")


@campus_bp.route("/multi_purpose_building")
def multi_purpose_building():
    return _floor_plan("Multi-Purpose Building", floor_count=2, base_url="multi_purpose_building")


@campus_bp.route("/power_room")
def power_room():
    return _floor_plan("Power Room", floor_count=1, base_url="power_room")


@campus_bp.route("/ylagan_hall")
def ylagan():
    return _floor_plan("Ylagan Hall", floor_count=2, base_url="ylagan_hall")


@campus_bp.route("/automotive_building")
def automotive():
    return _floor_plan("Automotive Building", floor_count=3, base_url="automotive_building")


_GROUND_FLOOR_ROOMS = [
    {"name": "Medical and Dental Services", "left": 1,  "top": 3,  "width": 13, "height": 38, "desc": "Student health and dental clinic",         "office_key": "Clinic"},
    {"name": "Record and Information Center","left": 14, "top": 3,  "width": 10, "height": 38, "desc": "Official school records and documents",   "office_key": "Registrar"},
    {"name": "MPC Cares",                    "left": 24, "top": 3,  "width": 10, "height": 38, "desc": "Student welfare and assistance"},
    {"name": "Faculty Room",                 "left": 34, "top": 3,  "width": 28, "height": 38, "desc": "Faculty lounge and workroom"},
    {"name": "CR",                           "left": 88, "top": 3,  "width": 11, "height": 38, "desc": "Comfort room"},
    {"name": "Quality Assurance Office",     "left": 1,  "top": 58, "width": 13, "height": 38, "desc": "Quality management and accreditation"},
    {"name": "Conference Room",              "left": 14, "top": 58, "width": 10, "height": 38, "desc": "Meeting and conference facility"},
    {"name": "Repair and Maintenance",       "left": 62, "top": 58, "width": 13, "height": 38, "desc": "Facilities maintenance office"},
    {"name": "Function Hall",                "left": 75, "top": 58, "width": 14, "height": 38, "desc": "Multi-purpose function hall"},
]

_ACADEMIC_FLOORS = {
    1: {"label": "Ground Floor", "image": None, "rooms": _GROUND_FLOOR_ROOMS},
}

_IT_FLOORS = {
    1: {"label": "Ground Floor", "image": None, "rooms": _GROUND_FLOOR_ROOMS},
}


@campus_bp.route("/academic_building")
def academic_building():
    return _floor_plan("Academic Building", floor_count=3,
                       base_url="academic_building",
                       custom_floors=_ACADEMIC_FLOORS)


@campus_bp.route("/waf_&_rac_building")
def waf_rac_building():
    return _floor_plan("WAF & RAC Building", floor_count=3, base_url="waf_&_rac_building")


_NEW_ADMIN_FLOORS = {
    1: {
        "label": "Ground Floor",
        "image": "images/floor_plans/new_admin_f1.png",
        "rooms": [
            # Top row  (left%, top%, width%, height%, office_key links to offices.key)
            {"name": "Medical and Dental Services", "left": 1,  "top": 3,  "width": 13, "height": 38, "desc": "Student health and dental clinic",           "office_key": "Clinic"},
            {"name": "Record and Information Center",   "left": 14, "top": 3,  "width": 10, "height": 38, "desc": "Official school records and documents",   "office_key": "Registrar"},
            {"name": "MPC Cares",                       "left": 24, "top": 3,  "width": 10, "height": 38, "desc": "Student welfare and assistance"},
            {"name": "Faculty Room",                    "left": 34, "top": 3,  "width": 28, "height": 38, "desc": "Faculty lounge and workroom"},
            {"name": "CR",                              "left": 88, "top": 3,  "width": 11, "height": 38, "desc": "Comfort room"},
            # Bottom row
            {"name": "Quality Assurance Office",        "left": 1,  "top": 58, "width": 13, "height": 38, "desc": "Quality management and accreditation"},
            {"name": "Conference Room",                 "left": 14, "top": 58, "width": 10, "height": 38, "desc": "Meeting and conference facility"},
            {"name": "Repair and Maintenance",          "left": 62, "top": 58, "width": 13, "height": 38, "desc": "Facilities maintenance office"},
            {"name": "Function Hall",                   "left": 75, "top": 58, "width": 14, "height": 38, "desc": "Multi-purpose function hall"},
        ],
    },
}


@campus_bp.route("/new_admin_building")
def new_admin_building():
    return _floor_plan("New Admin Building", floor_count=4,
                       base_url="new_admin_building",
                       custom_floors=_NEW_ADMIN_FLOORS)


@campus_bp.route("/old_admin_building")
def old_admin_building():
    return _floor_plan("Old Admin Building", floor_count=2, base_url="old_admin_building")


@campus_bp.route("/fsm_building")
def fsm_building():
    return _floor_plan("FSM Building", floor_count=3, base_url="fsm_building")


@campus_bp.route("/civil_tech_building")
def civil_tech_building():
    return _floor_plan("Civil Tech Building", floor_count=3, base_url="civil_tech_building")


@campus_bp.route("/waf_&_fsm_building")
def waf_fsm_building():
    return _floor_plan("WAF & FSM Building", floor_count=3, base_url="waf_&_fsm_building")


@campus_bp.route("/tech_building")
def tech_building():
    return _floor_plan("Tech Building", floor_count=4, base_url="tech_building")


@campus_bp.route("/graduate_school_building")
def graduate_school_building():
    return _floor_plan("Graduate School Building", floor_count=2, base_url="graduate_school_building")


@campus_bp.route("/mechanical_building")
def mechanical_building():
    return _floor_plan("Mechanical Building", floor_count=3, base_url="mechanical_building")


@campus_bp.route("/te_building")
def te_building():
    return _floor_plan("TE Building", floor_count=3, base_url="te_building")


@campus_bp.route("/science_building")
def science_building():
    return _floor_plan("Science Building", floor_count=4, base_url="science_building")


@campus_bp.route("/it_building")
def it_building():
    return _floor_plan("IT Building", floor_count=4,
                       base_url="it_building",
                       custom_floors=_IT_FLOORS)


@campus_bp.route("/engineering-floor1")
def engineering_floor1():
    return _floor_plan("Engineering Building", floor_count=1, base_url="engineering-floor1")
