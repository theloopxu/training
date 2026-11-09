"""Shared loaders for the Wilson scheduler tools. Read-only access to school/ and a run's intake."""
import csv
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
# WILSON_SCHOOL points the tools at another school folder, such as a hindcast of a real past term.
SCHOOL = Path(os.environ.get("WILSON_SCHOOL", HERE / "school"))
COMMONS = ("M", 15 * 60 + 45, 17 * 60)  # Monday 3:45 to 5:00 p.m., Fall 2027 (rule H6)
if (SCHOOL / "policy.json").exists():  # a past term predates Commons Hour: {"commons": null}
    _c = json.loads((SCHOOL / "policy.json").read_text(encoding="utf-8")).get("commons", "default")
    COMMONS = None if _c is None else COMMONS
ADJUNCT_EARLIEST = 16 * 60  # adjuncts teach evening blocks only


def mins(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[2:])


def hhmm(m):
    h, mm = divmod(m, 60)
    return f"{(h + 11) % 12 + 1}:{mm:02d}{'a' if h < 12 else 'p'}"


def rows(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def overlaps(days_a, a0, a1, days_b, b0, b1):
    return bool(set(days_a) & set(days_b)) and a0 < b1 and b0 < a1


def load_school():
    blocks = [{**b, "s": mins(b["start"]), "e": mins(b["end"])} for b in rows(SCHOOL / "grid.csv")]
    rooms = [{**r, "capacity": int(r["capacity"])} for r in rows(SCHOOL / "rooms.csv")]
    background = [{**b, "s": mins(b["start"]), "e": mins(b["end"])} for b in rows(SCHOOL / "background-fall-2027.csv")]
    courses = [{**c, **{k: int(c[k]) for k in ("sections", "in_person", "online_or_arranged", "cap")}}
               for c in rows(SCHOOL / "management-courses.csv")]
    faculty = [{**f, "fall_load": int(f["fall_load"]), "qualified": set(filter(None, f["qualified"].split(";"))),
                **{k: float(f[k]) for k in ("habit_morning", "habit_afternoon", "habit_evening")}}
               for f in rows(SCHOOL / "management-faculty.csv")]
    return blocks, rooms, background, courses, faculty


def load_intake(run):
    return json.loads((Path(run) / "intake.json").read_text(encoding="utf-8"))


def build_units(courses):
    """Teaching units: one per section, with cross-listed pairs merged (rule H7)."""
    units, pairs = [], {}
    for c in courses:
        level = "graduate" if c["course"].split()[1][0] >= "5" else "undergraduate"
        if c["crosslist"]:
            pairs.setdefault(c["crosslist"], []).append(c)
            continue
        for k in range(c["in_person"]):
            units.append({"id": f"{c['course']}#{k + 1}", "courses": [c["course"]], "title": c["title"],
                          "level": level, "mode": "in-person", "cap": c["cap"], "room_need": c["room_need"]})
        for k in range(c["online_or_arranged"]):
            mode = "online" if c["cap"] > 0 else "arranged"
            units.append({"id": f"{c['course']}#{c['in_person'] + k + 1}", "courses": [c["course"]], "title": c["title"],
                          "level": level, "mode": mode, "cap": c["cap"], "room_need": ""})
    for group in pairs.values():
        n = min(c["in_person"] for c in group)
        for k in range(n):
            names = [c["course"] for c in group]
            units.append({"id": "/".join(names) + f"#{k + 1}", "courses": names, "title": group[0]["title"],
                          "level": "undergraduate", "mode": "in-person", "cap": sum(c["cap"] for c in group),
                          "room_need": group[0]["room_need"]})
    return units


def daypart(start_min):
    if start_min < 12 * 60:
        return "morning"
    return "afternoon" if start_min < 17 * 60 else "evening"


def in_window(block, w):
    """True when the block meets on any day of the window and overlaps its hours."""
    return overlaps(block["days"], block["s"], block["e"], w["days"], mins(w["start"]), mins(w["end"]))


def inside_window(block, w):
    """Share of the block's meeting days that fall inside the window's days and hours (for preferences).
    Partial credit matters: "MW afternoons" has no MW-only daytime block, so an MWF afternoon block earns 2/3.
    (Run 2026-11-05_run-01 scored such requests as zero; the reviewer caught it.)
    A block is inside the hours when its midpoint is, so "mornings" (to 12:00) credits 11:15 to 12:10.
    (Run 2026-11-05_run-03 required the whole block inside; the reviewer caught that too.)"""
    mid = (block["s"] + block["e"]) / 2
    if not (mins(w["start"]) <= mid < mins(w["end"])):
        return 0.0
    return len(set(block["days"]) & set(w["days"])) / len(block["days"])
