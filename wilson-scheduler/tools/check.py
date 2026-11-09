"""
Independent hard-rule check of a finished schedule. Shares only the file
loaders with the solver; every rule is re-implemented here from
constraints/rules.md so the maker never grades its own work.

Writes <run>/check.md. Exits 1 if any hard rule is broken.

  python tools/check.py runs/2026-11-05_run-01
"""
import csv
import sys
from collections import Counter
from pathlib import Path

from common import COMMONS, load_intake, load_school, mins, overlaps


def clash(a, b):
    return set(a["days"]) & set(b["days"]) and mins(a["start"]) < mins(b["end"]) and mins(b["start"]) < mins(a["end"])


def main(run):
    run = Path(run)
    blocks, rooms, background, courses, faculty = load_school()
    intake = load_intake(run)
    said = {p["name"]: p for p in intake["instructors"]}
    sched = list(csv.DictReader(open(run / "schedule.csv", encoding="utf-8")))
    fac = {f["name"]: f for f in faculty}
    room = {r["room"]: r for r in rooms}
    grid = {b["block"]: b for b in blocks}
    timed = [r for r in sched if r["mode"] == "in-person"]
    fails, notes = [], []

    def fail(rule, msg):
        fails.append(f"{rule}: {msg}")

    # Every offered section appears exactly once (cross-lists counted per member course).
    expected = Counter()
    for c in courses:
        expected[c["course"]] += c["sections"]
    got = Counter()
    for r in sched:
        for c in r["courses"].split("/"):
            got[c] += 1
    for c, n in expected.items():
        if got[c] != n:
            fail("coverage", f"{c} expected {n} sections, schedule has {got[c]}")
    for r in sched:
        if r["mode"] == "UNASSIGNED":
            notes.append(f"{r['unit']} could not be placed; the chair must decide")

    for r in timed:
        b = grid.get(r["block"])
        if not b or (b["days"], b["start"], b["end"]) != (r["days"], r["start"], r["end"]):
            fail("H1/H2", f"{r['unit']} uses {r['days']} {r['start']}-{r['end']}, not a grid block")
            continue
        if r["level"] == "graduate" and b["kind"] != "one-night evening":
            fail("H2", f"{r['unit']} is graduate but meets {r['days']} {r['start']}")
        if COMMONS and overlaps(r["days"], mins(r["start"]), mins(r["end"]), *COMMONS):
            fail("H6", f"{r['unit']} overlaps Commons Hour")
        rm = room.get(r["room"])
        if not rm:
            fail("H4", f"{r['unit']} room {r['room']} does not exist")
            continue
        if rm["capacity"] < int(r["cap"]):
            fail("H5", f"{r['unit']} cap {r['cap']} exceeds {r['room']} capacity {rm['capacity']}")
        for bg in background:
            if bg["room"] == r["room"] and clash(r, bg):
                fail("H4", f"{r['unit']} collides with {bg['course']}-{bg['section']} in {r['room']}")

    for i, a in enumerate(timed):
        for b in timed[i + 1:]:
            if a["instructor"] == b["instructor"] and clash(a, b):
                fail("H3", f"{a['instructor']} double-booked: {a['unit']} and {b['unit']}")
            if a["room"] == b["room"] and clash(a, b):
                fail("H4", f"{a['room']} double-booked: {a['unit']} and {b['unit']}")

    load = Counter(r["instructor"] for r in sched if r["mode"] in ("in-person", "online"))
    for name, n in load.items():
        f = fac.get(name)
        if not f:
            fail("H10", f"{name} is not a Management instructor")
            continue
        target = int(said.get(name, {}).get("load", f["fall_load"]))
        limit = target + (1 if f["status"] == "full-time" else 0)
        if n > limit:
            fail("H11", f"{name} has {n} sections; limit {limit}")
        elif n > target:
            notes.append(f"{name} has an overload ({n} against {target}); needs chair and dean approval")

    for r in sched:
        name = r["instructor"]
        if r["mode"] not in ("in-person", "online") or name not in fac:
            continue
        listed = {c["course"] for c in said.get(name, {}).get("courses", [])}
        if not any(c in fac[name]["qualified"] | listed for c in r["courses"].split("/")):
            fail("H10", f"{name} teaches {r['courses']} without having taught or listed it")
        if r["mode"] != "in-person":
            continue
        windows = list(said.get(name, {}).get("unavailable", []))
        if fac[name]["status"] == "adjunct":
            windows.append({"days": "MTWRF", "start": "0000", "end": "1600"})
        for w in windows:
            if clash(r, w):
                fail("H9", f"{name} teaches {r['unit']} {r['days']} {r['start']} inside a can't-teach window "
                           f"({w.get('source', w['days'] + ' ' + w['start'] + '-' + w['end'])})")

    lab_courses = {c["course"] for c in courses if c["room_need"] == "lab"}
    for p in intake["instructors"]:
        for n in p.get("room_needs", []):
            if n.get("hard") and n.get("room_type") == "lab":
                lab_courses.add(n["course"])
    for r in timed:
        is_lab = room[r["room"]]["type"] == "lab"
        needs = any(c in lab_courses for c in r["courses"].split("/"))
        if needs and not is_lab:
            fail("room need", f"{r['unit']} needs the lab but is in {r['room']}")
        if is_lab and not needs:
            fail("room need", f"{r['unit']} is in the lab without needing it")

    lines = ["# Hard-rule check", "", f"Schedule: `{run.name}/schedule.csv`, {len(sched)} rows, {len(timed)} timed sections.", ""]
    lines += ["**Result: PASS.** No hard rule is broken." if not fails else f"**Result: FAIL.** {len(fails)} violations."]
    if fails:
        lines += ["", "## Violations", ""] + [f"- {f}" for f in fails]
    if notes:
        lines += ["", "## For the chair", ""] + [f"- {n}" for n in notes]
    (run / "check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{'PASS' if not fails else 'FAIL'}: {len(fails)} violations, {len(notes)} notes")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main(sys.argv[1])
