import json
import socket

from flask import Blueprint, Response, abort, render_template, request

from kiosk_app.db import db_connection

campus_bp = Blueprint("campus", __name__)


_cached_lan_ip: str | None = None


def _lan_ip() -> str:
    global _cached_lan_ip
    if _cached_lan_ip is not None:
        return _cached_lan_ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        _cached_lan_ip = ip
        return ip
    except Exception:
        return "127.0.0.1"


@campus_bp.route("/campus")
def campus():
    port = request.host.split(":")[-1] if ":" in request.host else "5000"
    lan_base_url = f"http://{_lan_ip()}:{port}"
    return render_template("campus.html", lan_base_url=lan_base_url)


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


    html = render_template(
        "campus.html",
        indoor_directions=indoor_directions,
        room_placements=room_placements,
        lan_base_url=lan_base_url,
    )
    return Response(html, headers={
        "Content-Type": "text/html; charset=utf-8",
        "X-Content-Type-Options": "nosniff",
    })


_VALID_LOCATIONS = {
    "GATE","LAST HORIZONTAL ROAD","MAIN HORIZONTAL ROAD","SECOND HORIZONTAL ROAD",
    "1ST VERTICAL ROAD","2ND VERTICAL ROAD","3RD VERTICAL ROAD","4TH VERTICAL ROAD",
    "5TH VERTICAL ROAD","6TH VERTICAL ROAD","7TH VERTICAL ROAD","8TH VERTICAL ROAD",
    "ACADEMIC BUILDING","INDUSTRIAL TECHNOLOGY BUILDING","FSM BUILDING","CIVIL TECH BUILDING",
    "TECH BUILDING","MECHANICAL / ELECTRONICS BUILDING","AUTOMOTIVE TECHNOLOGY BUILDING","WAF & RAC BUILDING",
    "SCIENCE BUILDING","NEW ADMIN BUILDING","OLD ADMIN BUILDING","YLAGAN HALL",
    "RODRIGUEZ BUILDING","MIST-NCTESD DORMITORY","MULTI-PURPOSE / MULTI-MEDIA BUILDING",
    "MIST-NCTESD BUILDING","TEACHER EDUCATION BUILDING","POWER ROOM","GRADUATE SCHOOL BUILDING",
    "FSM & WAFT BUILDING",
}


@campus_bp.route("/directions")
def directions_mobile():
    html = render_template("directions_mobile.html")
    return Response(html, headers={
        "Content-Type": "text/html; charset=utf-8",
        "X-Content-Type-Options": "nosniff",
    })


_ENTRANCE_BY_FLOOR = {
    # x/y = staircase center (so route visibly comes FROM stairs)
    # hY = corridor level (horizontal hallway between room rows)
    1: {"x": 50, "y": 67, "hY": 50},   # stairs at x=420-505, y=380-560 → center 67%
    2: {"x": 50, "y": 67, "hY": 50},   # same staircase position as floor 1
    3: {"x": 50, "y": 67, "hY": 50},   # same staircase position
    4: {"x": 50, "y": 67, "hY": 50},   # lower-middle stairs same as floors 1-3
    5: {"x": 12, "y": 20, "hY": 45},   # same as floor 4
}

@campus_bp.route("/api/floor_rooms")
def api_floor_rooms():
    building = request.args.get("building", "").strip().title()
    try:
        floor_num = int(request.args.get("floor", 1))
    except (ValueError, TypeError):
        floor_num = 1

    # Try DB rooms first
    with db_connection() as conn:
        db_rows = conn.execute(
            "SELECT room, pos_left, pos_top, pos_width, pos_height, description"
            " FROM rooms WHERE building=? COLLATE NOCASE AND floor=? ORDER BY pos_top, pos_left",
            (building, str(floor_num)),
        ).fetchall()

    if db_rows:
        rooms = [
            {
                "name": r["room"],
                "left": r["pos_left"],
                "top": r["pos_top"],
                "width": r["pos_width"],
                "height": r["pos_height"],
                "desc": r["description"] or "",
            }
            for r in db_rows
        ]
        bldg_entrances = _BUILDING_ENTRANCES.get(building, {})
        raw_e = bldg_entrances.get(floor_num, _ENTRANCE_BY_FLOOR.get(floor_num, _ENTRANCE_BY_FLOOR[1]))
        # Normalize both key spellings so mobile JS (uses hY) and kiosk JS (uses hallway_y) both work
        entrance = {
            "x": raw_e.get("x", 50),
            "y": raw_e.get("y", 96),
            "hY": raw_e.get("hY", raw_e.get("hallway_y", 50)),
            "hallway_y": raw_e.get("hallway_y", raw_e.get("hY", 50)),
        }
        return Response(json.dumps({"rooms": rooms, "entrance": entrance}),
                        content_type="application/json")

    # Fall back to hardcoded data
    floors_map = {"Academic Building": _ACADEMIC_FLOORS}
    floors = floors_map.get(building)
    if not floors or floor_num not in floors:
        return Response(json.dumps({"rooms": [], "entrance": _ENTRANCE_BY_FLOOR.get(1)}),
                        content_type="application/json")

    floor_data = floors[floor_num]
    rooms = [
        {
            "name": r["name"],
            "left": r["left"],
            "top": r["top"],
            "width": r["width"],
            "height": r["height"],
            "desc": r.get("desc", ""),
        }
        for r in floor_data.get("rooms", [])
    ]
    entrance = _ENTRANCE_BY_FLOOR.get(floor_num, _ENTRANCE_BY_FLOOR[1])
    return Response(json.dumps({"rooms": rooms, "entrance": entrance}),
                    content_type="application/json")


# Per-building, per-floor entrance points (image % coordinates).
# x/y = "you are here" pin position, hallway_y = main corridor Y for routing.
_BUILDING_ENTRANCES: dict = {
    "Tech Building": {
        # Floor 1: main entrance at bottom-center
        1: {"x": 50, "y": 92, "hallway_y": 55},
        # Floors 2-5: staircase on left side (beside staff room area)
        2: {"x": 9, "y": 20, "hallway_y": 55},
        3: {"x": 9, "y": 20, "hallway_y": 55},
        4: {"x": 9, "y": 20, "hallway_y": 55},
        5: {"x": 9, "y": 20, "hallway_y": 55},
    },
}


def _floor_plan(building_name: str, floor_count: int = 3, base_url: str = "",
                custom_floors: dict | None = None):
    """Generic floor_plan.html renderer for any building."""
    try:
        floor_number = int(request.args.get("floor", 1))
    except (ValueError, TypeError):
        floor_number = 1

    with db_connection() as conn:
        bf_rows = conn.execute(
            "SELECT floor_number, floor_label, floor_image FROM building_floors"
            " WHERE building = ? ORDER BY floor_number",
            (building_name,),
        ).fetchall()

        if bf_rows:
            rm_rows = conn.execute(
                "SELECT room, description, pos_left, pos_top, pos_width,"
                " pos_height, office_key, floor, room_color FROM rooms"
                " WHERE LOWER(building)=LOWER(?)"
                " ORDER BY floor, pos_top, pos_left",
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
                    "color": rm["room_color"] or "",
                })

            floors = {
                r["floor_number"]: {
                    "label": r["floor_label"],
                    "image": r["floor_image"],
                    "rooms": rooms_by_floor.get(str(r["floor_number"]), []),
                }
                for r in bf_rows
            }
        elif custom_floors is not None:
            floors = custom_floors
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
    entrance = (
        _BUILDING_ENTRANCES.get(building_name, {}).get(floor_number)
        or floor_data.get("entrance")
        or {"x": 50, "y": 96, "hallway_y": 50}
    )

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
        entrance_x=entrance["x"],
        entrance_y=entrance["y"],
        hallway_y=entrance.get("hallway_y", 50),
    )


@campus_bp.route("/rodriguez_building")
def rodriguez_building():
    return _floor_plan("Rodriguez Building", floor_count=3, base_url="rodriguez_building")


@campus_bp.route("/mist_ncestd_dorm")
def mist_ncestd_dorm():
    return _floor_plan("MIST-NCTESD Dormitory", floor_count=4, base_url="mist_ncestd_dorm")


@campus_bp.route("/mist_ncestd_building")
def mist_ncestd_building():
    return _floor_plan("MIST-NCTESD Building", floor_count=3, base_url="mist_ncestd_building")


@campus_bp.route("/multi_purpose_building")
def multi_purpose_building():
    return _floor_plan("Multi-Purpose / Multi-Media Building", floor_count=2, base_url="multi_purpose_building")


@campus_bp.route("/power_room")
def power_room():
    return _floor_plan("Power Room", floor_count=1, base_url="power_room")


@campus_bp.route("/ylagan_hall")
def ylagan():
    return _floor_plan("Ylagan Hall", floor_count=2, base_url="ylagan_hall")


@campus_bp.route("/automotive_building")
def automotive():
    return _floor_plan("Automotive Technology Building", floor_count=3, base_url="automotive_building")


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
    # ── Top row (north side): top=8, height=36 ─────────────────────────────
    # Cols 1-2 (x=7–14)
    {
        "name": "VP for Admin and Finance",
        "left": 7, "top": 8, "width": 7, "height": 36,
        "desc": "Office of the Vice President for Administration and Finance",
        "directions": [
            "From the staircase, turn left along the north hallway.",
            "VP for Administration and Finance is the first office on your right.",
        ],
    },
    # Cols 2-3 (x=14–20)
    {
        "name": "VP for Academic Affairs",
        "left": 14, "top": 8, "width": 6, "height": 36,
        "desc": "Office of the Vice President for Academic Affairs",
        "directions": [
            "From the staircase, turn left along the north hallway.",
            "VP for Academic Affairs is the second office on your right.",
        ],
    },
    # Cols 3-4 (x=20–27)
    {
        "name": "VP for Research, Extension, Linkages and Quality Assurance",
        "left": 20, "top": 8, "width": 7, "height": 36,
        "desc": "Office of the Vice President for Research, Extension, Linkages and Quality Assurance",
        "directions": [
            "From the staircase, turn left along the north hallway.",
            "VP for Research is the third office on your right.",
        ],
    },
    # Col 4-5 (x=27–33)
    {
        "name": "Budget Office",
        "left": 27, "top": 8, "width": 6, "height": 36,
        "desc": "Budget and financial planning office",
        "directions": [
            "From the staircase, turn left along the north hallway.",
            "The Budget Office is the fourth door on your right.",
        ],
    },
    # Col 5-6 (x=33–40)
    {
        "name": "Accounting Office",
        "left": 33, "top": 8, "width": 7, "height": 36,
        "desc": "Accounting and financial records office",
        "directions": [
            "From the staircase, turn left along the north hallway.",
            "The Accounting Office is the fifth door on your right.",
        ],
    },
    # Col 6-7 (x=40–47)
    {
        "name": "Program Chair's Office and Field Study Center",
        "left": 40, "top": 8, "width": 7, "height": 36,
        "desc": "Program Chair's Office and Field Study Center",
        "directions": [
            "From the staircase, the Program Chair's Office is directly across the hallway to your left.",
        ],
    },
    # Col 7-8 (x=47–53)
    {
        "name": "Dean for Technology and Instruction Office",
        "left": 47, "top": 8, "width": 6, "height": 36,
        "desc": "Dean for Technology and Instruction Office",
        "directions": [
            "From the staircase, turn right along the north hallway.",
            "The Dean for Technology and Instruction Office is the first door on your left.",
        ],
    },
    # Cols 8-10 (x=53–66) — wider room
    {
        "name": "Dean for Graduate School and Program Chair of Graduate School",
        "left": 53, "top": 8, "width": 13, "height": 36,
        "desc": "Dean for Graduate School and Program Chair of Graduate School Office",
        "directions": [
            "From the staircase, turn right along the north hallway.",
            "Continue past the Dean for Technology Office.",
            "The Dean for Graduate School Office is the wide room on your left.",
        ],
    },
    # Cols 10-11 (x=66–73)
    {"name": "CR", "left": 66, "top": 8, "width": 7, "height": 36, "desc": "Comfort rooms (Female and Male)"},

    # ── Bottom row (south side): top=56, height=34 ─────────────────────────
    # Col 1-2 (x=7–14)
    {
        "name": "College President",
        "left": 7, "top": 56, "width": 7, "height": 34,
        "desc": "Office of the College President",
        "directions": [
            "From the staircase, cross the hallway to the south side.",
            "Turn left. The College President's Office is at the far left corner.",
        ],
    },
    # Col 2-3 (x=14–20)
    {
        "name": "Board of Secretary Office",
        "left": 14, "top": 56, "width": 6, "height": 34,
        "desc": "Board of Directors / Secretary's Office",
        "directions": [
            "From the staircase, cross to the south side and turn left.",
            "The Board of Secretary Office is next to the College President's Office.",
        ],
    },
    # Col 3-4 (x=20–27)
    {
        "name": "Conference Room",
        "left": 20, "top": 56, "width": 7, "height": 34,
        "desc": "Meeting and conference facility",
        "directions": [
            "From the staircase, cross to the south side and turn left.",
            "The Conference Room is the third door on your right.",
        ],
    },
    # Col 4-5 (x=27–33) — storage before left stairs
    {"name": "Storage", "left": 27, "top": 56, "width": 6, "height": 34, "desc": "Storage room"},
    # [LEFT EXIT STAIRS x=33–40 — not a room]
    # [RIGHT EXIT STAIRS x=47–53 — not a room]
    # Col 8-9 (x=55–62) — storage after right stairs
    {"name": "Storage", "left": 55, "top": 56, "width": 7, "height": 34, "desc": "Storage room"},
    # Cols 9-13 (x=62–93)
    {
        "name": "Content Creator Laboratory",
        "left": 62, "top": 56, "width": 31, "height": 34,
        "desc": "Content creation and digital media laboratory",
        "directions": [
            "From the staircase, cross to the south side and turn right.",
            "The Content Creator Laboratory occupies the large room at the far right.",
        ],
    },
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
        "directions": [
            "From the staircase on the 4th floor, turn left.",
            "The Computer Library will be on your left.",
        ],
    },
    {
        "name": "Educational Technology Room",
        "left": 67.5, "top": 54.3, "width": 25.8, "height": 37.1,
        "desc": "Educational technology and multimedia room",
        "directions": [
            "From the staircase on the 4th floor, turn right.",
            "The Educational Technology Room will be at the end of the hallway on your right.",
        ],
    },
]

_ACADEMIC_5TH_ROOMS = [
    {
        "name": "Staff Room",
        "left": 17.5, "top": 8.6, "width": 8.3, "height": 37.1,
        "desc": "Staff office",
        "directions": [
            "From the staircase on the 5th floor, the Staff Room will be directly ahead on your left.",
        ],
    },
    {"name": "CR", "left": 83.3, "top": 8.6, "width": 10.0, "height": 37.1, "desc": "Comfort room"},
]

_ACADEMIC_FLOORS = {
    1: {"label": "1st floor", "image": "images/floor_plans/academic_ground.svg", "rooms": _ACADEMIC_GROUND_ROOMS,
        "entrance": {"x": 50, "y": 67, "hallway_y": 50}},
    2: {"label": "2nd floor", "image": "images/floor_plans/academic_2nd.svg",    "rooms": _ACADEMIC_2ND_ROOMS,
        "entrance": {"x": 50, "y": 67, "hallway_y": 50}},
    3: {"label": "3rd floor", "image": "images/floor_plans/academic_3rd.svg",    "rooms": _ACADEMIC_3RD_ROOMS,
        "entrance": {"x": 43, "y": 73, "hallway_y": 50}},
    4: {"label": "4th floor", "image": "images/floor_plans/academic_4th.svg",    "rooms": _ACADEMIC_4TH_ROOMS,
        "entrance": {"x": 50, "y": 67, "hallway_y": 50}},
    5: {"label": "5th floor", "image": "images/floor_plans/academic_5th.svg",    "rooms": _ACADEMIC_5TH_ROOMS,
        "entrance": {"x": 12, "y": 30, "hallway_y": 45}},
}

_IT_FLOORS = {
    1: {"label": "1st floor", "image": "images/floor_plans/IT_1ST.JPG", "rooms": []},
    2: {"label": "2nd floor", "image": "images/floor_plans/IT_2ND.JPG", "rooms": []},
    3: {"label": "3rd floor", "image": "images/floor_plans/IT_3RD.JPG", "rooms": []},
    4: {"label": "4th floor", "image": None, "rooms": []},
}


@campus_bp.route("/academic_building")
def academic_building():
    return _floor_plan("Academic Building", floor_count=5, base_url="academic_building")


@campus_bp.route("/waf_&_rac_building")
def waf_rac_building():
    return _floor_plan("WAF & RAC Building", floor_count=3, base_url="waf_&_rac_building")


_NEW_ADMIN_FLOORS = {
    1: {
        "label": "Ground Floor",
        "image": "images/floor_plans/new_admin_f1.svg",
        "rooms": [
            # Coords = % of full SVG image (1200×700). Building outer: x=80-1120, y=60-640.
            # Top row (SVG y=77, h=220 → top=11%, height=31%)
            {"name": "Medical and Dental Services",   "left": 8,  "top": 11, "width": 11, "height": 31, "desc": "Student health and dental clinic",           "office_key": "Clinic"},
            {"name": "Record and Information Center", "left": 19, "top": 11, "width": 9,  "height": 31, "desc": "Official school records and documents",       "office_key": "Registrar"},
            {"name": "MPC Cares",                     "left": 28, "top": 11, "width": 9,  "height": 31, "desc": "Student welfare and assistance"},
            {"name": "Faculty Room",                  "left": 37, "top": 11, "width": 24, "height": 31, "desc": "Faculty lounge and workroom"},
            {"name": "CR",                            "left": 83, "top": 11, "width": 10, "height": 31, "desc": "Comfort room"},
            # Bottom row (SVG y=396, h=224 → top=57%, height=32%)
            {"name": "Quality Assurance Office",      "left": 8,  "top": 57, "width": 11, "height": 32, "desc": "Quality management and accreditation"},
            {"name": "Conference Room",               "left": 19, "top": 57, "width": 9,  "height": 32, "desc": "Meeting and conference facility"},
            {"name": "Repair and Maintenance",        "left": 60, "top": 57, "width": 11, "height": 32, "desc": "Facilities maintenance office"},
            {"name": "Function Hall",                 "left": 71, "top": 57, "width": 12, "height": 32, "desc": "Multi-purpose function hall"},
        ],
        "entrance": {"x": 52, "y": 73, "hallway_y": 48},
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
    return _floor_plan("Civil Technology Building", floor_count=4, base_url="civil_tech_building")


@campus_bp.route("/waf_&_fsm_building")
def waf_fsm_building():
    return _floor_plan("FSM & WAFT Building", floor_count=3, base_url="waf_&_fsm_building")


@campus_bp.route("/tech_building")
def tech_building():
    return _floor_plan("Tech Building", floor_count=5, base_url="tech_building")


@campus_bp.route("/graduate_school_building")
def graduate_school_building():
    return _floor_plan("Graduate School Building", floor_count=2, base_url="graduate_school_building")


@campus_bp.route("/graduate_school_annex")
def graduate_school_annex():
    return _floor_plan("Graduate School Annex", floor_count=2, base_url="graduate_school_annex")


@campus_bp.route("/mechanical_building")
def mechanical_building():
    return _floor_plan("Mechanical / Electronics Building", floor_count=3, base_url="mechanical_building")


@campus_bp.route("/te_building")
def te_building():
    return _floor_plan("Teacher Education Building", floor_count=3, base_url="te_building")


@campus_bp.route("/science_building")
def science_building():
    return _floor_plan("Science Building", floor_count=4, base_url="science_building")


@campus_bp.route("/it_building")
def it_building():
    return _floor_plan("Industrial Technology Building", floor_count=3, base_url="it_building")


@campus_bp.route("/engineering-floor1")
def engineering_floor1():
    return _floor_plan("Engineering Building", floor_count=1, base_url="engineering-floor1")


@campus_bp.route("/building/<slug>")
def dynamic_building(slug: str):
    """Serves any building that has floor data in the DB but no hardcoded route."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT page_url, name FROM campus_pins WHERE page_url = ?",
            (f"/building/{slug}",),
        ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT name FROM buildings WHERE LOWER(REPLACE(name,' ','_')) = ?",
                (slug.lower(),),
            ).fetchone()
        if row is None:
            abort(404)
        building_name = row["name"]
        has_floors = conn.execute(
            "SELECT 1 FROM building_floors WHERE building = ? LIMIT 1",
            (building_name,),
        ).fetchone()
        if not has_floors:
            abort(404)
    return _floor_plan(building_name, base_url=f"building/{slug}")
