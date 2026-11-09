"""
Validate <run>/intake.json against the intake schema in agents/intake.md
and against school/. Run after the intake agent, before the solver.

  python tools/validate_intake.py runs/2026-11-05_run-01
"""
import re
import sys
from pathlib import Path

from common import load_intake, load_school

TIME = re.compile(r"^([01]\d|2[0-4])[0-5]\d$")


def main(run):
    _, _, _, courses, faculty = load_school()
    intake = load_intake(Path(run))
    names = {f["name"] for f in faculty}
    offered = {c["course"] for c in courses}
    errs = []
    for key in ("term", "source", "instructors", "open_questions"):
        if key not in intake:
            errs.append(f"missing top-level key: {key}")
    for p in intake.get("instructors", []):
        who = p.get("name", "?")
        if who not in names:
            errs.append(f"{who}: not in school/management-faculty.csv")
        if not isinstance(p.get("load"), int) or not p.get("load_source"):
            errs.append(f"{who}: load must be an integer with a load_source")
        for c in p.get("courses", []):
            if c.get("course") not in offered:
                errs.append(f"{who}: {c.get('course')} is not offered in Fall 2027")
            if not isinstance(c.get("rank"), int):
                errs.append(f"{who}: {c.get('course')} needs an integer rank")
        for kind in ("unavailable", "prefer", "avoid"):
            for w in p.get(kind, []):
                if not w.get("days") or set(w["days"]) - set("MTWRF"):
                    errs.append(f"{who}: {kind} window has bad days {w.get('days')!r}")
                if not (TIME.match(str(w.get("start", ""))) and TIME.match(str(w.get("end", "")))):
                    errs.append(f"{who}: {kind} window needs HHMM start and end")
                if not w.get("source"):
                    errs.append(f"{who}: {kind} window has no source quote")
        for n in p.get("room_needs", []):
            if not n.get("source"):
                errs.append(f"{who}: room need for {n.get('course')} has no source quote")
    for q in intake.get("open_questions", []):
        if not (q.get("who") and q.get("question") and q.get("default")):
            errs.append(f"open question needs who, question and default: {q}")
    if errs:
        print("INVALID\n" + "\n".join(f"- {e}" for e in errs))
        sys.exit(1)
    print(f"VALID: {len(intake['instructors'])} instructors, {len(intake['open_questions'])} open questions")


if __name__ == "__main__":
    main(sys.argv[1])
