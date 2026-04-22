import socket

from flask import Blueprint, Response, render_template, request

from kiosk_app.db import db_connection

campus_bp = Blueprint("campus", __name__)


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@campus_bp.route("/campus")
def campus():
    with db_connection() as conn:
        rows = conn.execute("SELECT DISTINCT building FROM rooms").fetchall()
    buildings = [row[0] for row in rows]

    port = request.host.split(":")[-1] if ":" in request.host else "5000"
    lan_base_url = f"http://{_lan_ip()}:{port}"
    return render_template("campus.html", buildings=buildings, lan_base_url=lan_base_url)


@campus_bp.route("/campus_map")
def campus_map():
    indoor_directions: dict[str, dict[str, list[str]]] = {}
    room_placements: dict[str, dict[str, dict[str, float]]] = {}

    for building_name, floors in (("Academic Building", _ACADEMIC_FLOORS),):
        rooms_dirs: dict[str, list[str]] = {}
        rooms_pos: dict[str, dict[str, float]] = {}
        for floor in floors.values():
            for room in floor.get("rooms", []) or []:
                name_key = room["name"].upper()
                directions = room.get("directions")
                if directions:
                    rooms_dirs[name_key] = list(directions)
                rooms_pos[name_key] = {
                    "left":   float(room.get("left", 0)),
                    "top":    float(room.get("top", 0)),
                    "width":  float(room.get("width", 10)),
                    "height": float(room.get("height", 10)),
                    "floor":  next((n for n, f in floors.items() if room in f.get("rooms", [])), 1),
                }
        key = building_name.upper()
        if rooms_dirs:
            indoor_directions[key] = rooms_dirs
        if rooms_pos:
            room_placements[key] = rooms_pos

    port = request.host.split(":")[-1] if ":" in request.host else "5000"
    lan_base_url = f"http://{_lan_ip()}:{port}"


    return render_template(
        "campus.html",
        indoor_directions=indoor_directions,
        room_placements=room_placements,
        lan_base_url=lan_base_url,
    )


_VALID_LOCATIONS = {
    "GATE","LAST HORIZONTAL ROAD","MAIN HORIZONTAL ROAD","SECOND HORIZONTAL ROAD",
    "1ST VERTICAL ROAD","2ND VERTICAL ROAD","3RD VERTICAL ROAD","4TH VERTICAL ROAD",
    "5TH VERTICAL ROAD","6TH VERTICAL ROAD","7TH VERTICAL ROAD","8TH VERTICAL ROAD",
    "ACADEMIC BUILDING","IT BUILDING","FSM BUILDING","CIVIL TECH BUILDING",
    "TECH BUILDING","MECHANICAL BUILDING","AUTOMOTIVE BUILDING","WAF & RAC BUILDING",
    "SCIENCE BUILDING","NEW ADMIN BUILDING","OLD ADMIN BUILDING","YLAGAN HALL",
    "RODRIGUEZ BUILDING","MIST-NCESTD DORM","MULTI-PURPOSE BUILDING",
    "MIST-NCESTD BUILDING","TE BUILDING","POWER ROOM","GRADUATE SCHOOL BUILDING",
}


@campus_bp.route("/directions")
def directions_mobile():
    html = render_template("directions_mobile.html")
    return Response(html, headers={
        "Content-Type": "text/html; charset=utf-8",
        "X-Content-Type-Options": "nosniff",
    })


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

    all_rooms_index = [
        {
            "name": r["name"],
            "floor": n,
            "floor_label": f["label"],
            "url": f"/{base_url}?floor={n}&location=" + r["name"].replace(" ", "+"),
        }
        for n, f in floors.items()
        for r in f.get("rooms", [])
    ]

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
        all_rooms_index=all_rooms_index,
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


_ACADEMIC_GROUND_ROOMS = [
    {
        "name": "Medical and Dental Services",
        "left": 6.7, "top": 8.6, "width": 16.7, "height": 37.1,
        "desc": "Student health and dental clinic",
        "office_key": "Clinic",
        "directions": [
            "After entering the building, proceed straight ahead.",
            "Turn left at the hallway.",
            "Continue down the corridor.",
            "The Medical and Dental Services will be on your right.",
        ],
    },

    {
        "name": "Record and Information Center",
        "left": 23.3, "top": 8.6, "width": 11.7, "height": 37.1,
        "desc": "Official school records and documents",
        "office_key": "Registrar",
    },
    {
        "name": "MPC Cares",
        "left": 35.0, "top": 8.6, "width": 9.2, "height": 37.1,
        "desc": "Student welfare and assistance",
    },
    {
        "name": "Faculty Room",
        "left": 44.2, "top": 8.6, "width": 33.3, "height": 37.1,
        "desc": "Faculty lounge and workroom",
        "directions": [
            "After entering the building, proceed straight ahead.",
            "The faculty entrance will be directly in front of you.",
        ],
    },

    {
        "name": "CR",
        "left": 83.3, "top": 8.6, "width": 10.0, "height": 37.1,
        "desc": "Comfort room",
    },
    {
        "name": "Quality Assurance Office",
        "left": 6.7, "top": 54.3, "width": 16.7, "height": 37.1,
        "desc": "Quality management and accreditation",
        "directions": [
            "After entering the building, proceed straight ahead.",
            "Turn left at the hallway.",
            "Continue down the corridor.",
            "The Quality Assurance Office will be on your left.",
        ],

    },
    {
        "name": "Conference Room",
        "left": 23.3, "top": 54.3, "width": 11.7, "height": 37.1,
        "desc": "Meeting and conference facility",
    },
    {
        "name": "Repair and Maintenance",
        "left": 67.5, "top": 54.3, "width": 12.9, "height": 37.1,
        "desc": "Facilities maintenance office",
    },
    {
        "name": "Function Hall",
        "left": 80.4, "top": 54.3, "width": 12.9, "height": 37.1,
        "desc": "Multi-purpose function hall",
    },
]

_GO_UPSTAIRS_2 = [
    "After entering the building, proceed straight ahead toward the staircase/elevator.",
    "Go up the stairs to the 2nd floor.",
]
_GO_UPSTAIRS_3 = [
    "After entering the building, proceed straight ahead toward the staircase/elevator.",
    "Go up the stairs to the 3rd floor.",
]
_GO_UPSTAIRS_4 = [
    "After entering the building, proceed straight ahead toward the staircase/elevator.",
    "Go up the stairs to the 4th floor.",
]
_GO_UPSTAIRS_5 = [
    "After entering the building, proceed straight ahead toward the staircase/elevator.",
    "Go up the stairs to the 5th floor.",
]

_ACADEMIC_2ND_ROOMS = [
    {
        "name": "Director for Student Affairs",
        "left": 6.7, "top": 8.6, "width": 10.8, "height": 37.1,
        "desc": "Office of the Director for Student Affairs",
        "office_key": "OSA",
        "directions": [
            "After entering the building, proceed straight ahead toward the staircase/elevator.",
            "Go up the stairs to the next floor.",
            "At the top of the stairs, turn left into the hallway.",
            "Continue straight to the end of the corridor.",
            "The Office of Student Affairs will be on your right.",
        ],
    },
    {
        "name": "Guidance Scholarship & Admission",
        "left": 17.5, "top": 8.6, "width": 14.2, "height": 37.1,
        "desc": "Guidance, counselling, scholarship, and admission services",
        "office_key": "Guidance",
        "directions": [
            "After entering the building, proceed straight ahead toward the staircase/elevator.",
            "Go up the stairs to the next floor.",
            "At the top of the stairs, turn left along the hallway.",
            "Continue straight down the corridor.",
            "The Guidance and Counselling Office will be on your right.",
        ],
    },
    {
        "name": "Placement and Follow-Up",
        "left": 31.7, "top": 8.6, "width": 10.8, "height": 37.1,
        "desc": "Career placement and alumni follow-up services",
        "office_key": "PLACEMENT",
        "directions": [
            "After entering the building, proceed straight ahead toward the staircase/elevator.",
            "Go up the stairs to the next floor.",
            "At the top of the stairs, turn left along the hallway.",
            "Continue straight down the corridor.",
            "The Placement and Follow-Up Office will be on your right.",
        ],
    },
    {
        "name": "Faculty Room",
        "left": 53.3, "top": 8.6, "width": 24.2, "height": 37.1,
        "desc": "Faculty lounge and workroom",
    },
    {"name": "CR", "left": 83.3, "top": 8.6, "width": 10.0, "height": 37.1, "desc": "Comfort room"},
    {"name": "Classroom", "left": 6.7, "top": 54.3, "width": 28.3, "height": 37.1, "desc": "General classroom"},
    {"name": "Command Center 1", "left": 67.5, "top": 54.3, "width": 13.3, "height": 37.1, "desc": "Command center"},
    {"name": "Command Center 2", "left": 80.8, "top": 54.3, "width": 12.5, "height": 37.1, "desc": "Command center"},
]

_ACADEMIC_3RD_ROOMS = [
    {
        "name": "VP for Admin and Finance",
        "left": 6.7, "top": 8.6, "width": 9.2, "height": 37.1,
        "desc": "Office of the Vice President for Administration and Finance",
        "directions": _GO_UPSTAIRS_3 + [
            "At the top of the stairs, turn left along the hallway.",
            "The Office of the VP for Administration and Finance will be the first door on your right.",
        ],
    },
    {
        "name": "VP for Academic Affairs",
        "left": 15.8, "top": 8.6, "width": 9.2, "height": 37.1,
        "desc": "Office of the Vice President for Academic Affairs",
        "directions": _GO_UPSTAIRS_3 + [
            "At the top of the stairs, turn left along the hallway.",
            "The Office of the VP for Academic Affairs will be the second door on your right.",
        ],
    },
    {
        "name": "Program Chair's Office and Field Study Center",
        "left": 52.5, "top": 8.6, "width": 8.3, "height": 37.1,
        "desc": "Program Chair's Office and Field Study Center",
        "directions": _GO_UPSTAIRS_3 + [
            "At the top of the stairs, turn right along the hallway.",
            "The Program Chair's Office and Field Study Center will be on your right.",
        ],
    },
    {
        "name": "Dean for Technology and Instruction Office",
        "left": 60.8, "top": 8.6, "width": 8.3, "height": 37.1,
        "desc": "Dean for Technology and Instruction Office",
        "directions": _GO_UPSTAIRS_3 + [
            "At the top of the stairs, turn right along the hallway.",
            "The Dean for Technology and Instruction Office will be on your right.",
        ],
    },
    {
        "name": "Dean for Graduate School and Program Chair of Graduate School",
        "left": 69.2, "top": 8.6, "width": 8.3, "height": 37.1,
        "desc": "Dean for Graduate School and Program Chair of Graduate School Office",
        "directions": _GO_UPSTAIRS_3 + [
            "At the top of the stairs, turn right along the hallway.",
            "Continue straight to the end of the corridor.",
            "The Dean for Graduate School Office will be on your right.",
        ],
    },
    {"name": "CR", "left": 83.3, "top": 8.6, "width": 10.0, "height": 37.1, "desc": "Comfort room"},
    {"name": "Classroom", "left": 6.7, "top": 54.3, "width": 28.3, "height": 37.1, "desc": "General classroom"},
    {"name": "Command Center 1", "left": 67.5, "top": 54.3, "width": 13.3, "height": 37.1, "desc": "Command center"},
    {"name": "Command Center 2", "left": 80.8, "top": 54.3, "width": 12.5, "height": 37.1, "desc": "Command center"},
]

_ACADEMIC_4TH_ROOMS = [
    {
        "name": "Library",
        "left": 17.5, "top": 8.6, "width": 60.0, "height": 37.1,
        "desc": "Main academic library",
        "office_key": "LIBRARY",
        "directions": [
            "After entering the building, proceed straight ahead toward the staircase/elevator.",
            "Go up the stairs to the 4th floor.",
            "At the top of the stairs, turn right into the hallway.",
            "Continue straight along the hallway.",
            "The entrance of the Library will be on your left.",
        ],
    },
    {"name": "CR", "left": 83.3, "top": 8.6, "width": 10.0, "height": 37.1, "desc": "Comfort room"},
    {
        "name": "Computer Library",
        "left": 6.7, "top": 54.3, "width": 28.3, "height": 37.1,
        "desc": "Computer library and e-resources",
        "directions": _GO_UPSTAIRS_4 + [
            "At the top of the stairs, turn left into the hallway.",
            "The Computer Library will be on your left.",
        ],
    },
    {
        "name": "Educational Technology Room",
        "left": 67.5, "top": 54.3, "width": 25.8, "height": 37.1,
        "desc": "Educational technology and multimedia room",
        "directions": _GO_UPSTAIRS_4 + [
            "At the top of the stairs, turn right into the hallway.",
            "The Educational Technology Room will be at the end of the hallway on your right.",
        ],
    },
]

_ACADEMIC_5TH_ROOMS = [
    {
        "name": "Staff Room",
        "left": 17.5, "top": 8.6, "width": 8.3, "height": 37.1,
        "desc": "Staff office",
        "directions": _GO_UPSTAIRS_5 + [
            "At the top of the stairs, the Staff Room will be directly ahead on your left.",
        ],
    },
    {
        "name": "Control Room",
        "left": 17.5, "top": 54.3, "width": 8.3, "height": 37.1,
        "desc": "Control and monitoring room",
        "directions": _GO_UPSTAIRS_5 + [
            "At the top of the stairs, the Control Room will be on your left below the Staff Room.",
        ],
    },
    {"name": "CR", "left": 83.3, "top": 8.6, "width": 10.0, "height": 37.1, "desc": "Comfort room"},
]

_ACADEMIC_FLOORS = {
    1: {"label": "1st floor", "image": "images/floor_plans/academic_ground.svg", "rooms": _ACADEMIC_GROUND_ROOMS},
    2: {"label": "2nd floor", "image": "images/floor_plans/academic_2nd.svg",    "rooms": _ACADEMIC_2ND_ROOMS},
    3: {"label": "3rd floor", "image": "images/floor_plans/academic_3rd.svg",    "rooms": _ACADEMIC_3RD_ROOMS},
    4: {"label": "4th floor", "image": "images/floor_plans/academic_4th.svg",    "rooms": _ACADEMIC_4TH_ROOMS},
    5: {"label": "5th floor", "image": "images/floor_plans/academic_5th.svg",    "rooms": _ACADEMIC_5TH_ROOMS},
}

_IT_FLOORS = {
    1: {"label": "1st floor", "image": "images/floor_plans/IT_1ST.JPG", "rooms": []},
    2: {"label": "2nd floor", "image": "images/floor_plans/IT_2ND.JPG", "rooms": []},
    3: {"label": "3rd floor", "image": "images/floor_plans/IT_3RD.JPG", "rooms": []},
    4: {"label": "4th floor", "image": None, "rooms": []},
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
