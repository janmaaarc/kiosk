from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "welcome":        {"en": "WELCOME",               "fil": "MALIGAYANG PAGDATING"},
    "faculty":        {"en": "FACULTY",                "fil": "MGA GURO"},
    "campus_map":     {"en": "CAMPUS MAP",             "fil": "MAPA NG KAMPUS"},
    "office_info":    {"en": "OFFICE INFORMATION",     "fil": "IMPORMASYON SA OPISINA"},
    "announcements":  {"en": "DIGITAL ANNOUNCEMENT",   "fil": "DIGITAL NA ANUNSYO"},
    "events":         {"en": "EVENT AND ACTIVITIES",   "fil": "MGA KAGANAPAN AT AKTIBIDAD"},
    "about":          {"en": "ABOUT US",               "fil": "TUNGKOL SA AMIN"},
    "lang_toggle":    {"en": "FILIPINO",               "fil": "ENGLISH"},
    "search_title":   {"en": "Campus Room Finder",     "fil": "Paghahanap ng Silid"},
    "search_label":   {"en": "Enter Room Number",      "fil": "Ilagay ang Numero ng Silid"},
    "search_button":  {"en": "Search",                 "fil": "Hanapin"},
}


def get_translator(lang: str):
    def t(key: str) -> str:
        entry = STRINGS.get(key, {})
        return entry.get(lang) or entry.get("en") or key
    return t
