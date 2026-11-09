"""
Place every Management section for Fall 2027: instructor, time block and room.

Reads school/, constraints/weights.json and <run>/intake.json. Writes
<run>/schedule.csv and <run>/solver-log.json. Hard rules (constraints/rules.md
H1 to H11) are constraints; soft rules S1 to S10 are a weighted score.

A section the model cannot place is reported as unassigned at a large penalty,
so the solver always returns a schedule and says exactly what did not fit.

  python tools/solve.py runs/2026-11-05_run-01
  python tools/solve.py runs/2026-11-05_run-02 --baseline runs/2026-11-05_run-01

With --baseline, the previous run's placements become the starting point and
each placement kept earns the stability weight, so a rerun after one changed
answer moves only what it must.
"""
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from common import (ADJUNCT_EARLIEST, COMMONS, HERE, build_units, daypart, in_window, inside_window,
                    load_intake, load_school, overlaps)

SCALE = 10


def main(run, baseline=None):
    run = Path(run)
    W = json.loads((HERE / "constraints/weights.json").read_text(encoding="utf-8"))
    blocks, rooms, background, courses, faculty = load_school()
    intake = load_intake(run)
    said = {p["name"]: p for p in intake["instructors"]}
    units = build_units(courses)
    placed = [u for u in units if u["mode"] == "in-person"]
    online = [u for u in units if u["mode"] == "online"]
    arranged = [u for u in units if u["mode"] == "arranged"]

    # ---- instructors: defaults from school/, overrides from intake ----
    people = {}
    for f in faculty:
        p = said.get(f["name"], {})
        ranks = {c["course"]: c["rank"] for c in p.get("courses", [])}
        unavailable = list(p.get("unavailable", []))
        if f["status"] == "adjunct":
            unavailable.append({"days": "MTWRF", "start": "0000", "end": f"{ADJUNCT_EARLIEST // 60:02d}00",
                                "source": "adjuncts teach evening blocks only"})
        people[f["name"]] = {
            "status": f["status"], "load": int(p.get("load", f["fall_load"])),
            "qualified": f["qualified"] | set(ranks), "ranks": ranks, "unavailable": unavailable,
            "prefer": p.get("prefer", []), "avoid": p.get("avoid", []),
            "same_room": bool(p.get("same_room_back_to_back")), "b2b2b_ok": bool(p.get("back_to_back_to_back_ok")),
            "habit": {"morning": f["habit_morning"], "afternoon": f["habit_afternoon"], "evening": f["habit_evening"]},
            "answered": f["name"] in said,
        }

    # ---- legal blocks per unit (H1, H2, H6) ----
    commons_blocked = [b["block"] for b in blocks if COMMONS and overlaps(b["days"], b["s"], b["e"], *COMMONS)]
    def legal_blocks(u):
        out = []
        for b in blocks:
            if b["block"] in commons_blocked:
                continue
            if u["level"] == "graduate" and b["kind"] != "one-night evening":
                continue
            out.append(b)
        return out

    # ---- rooms free of background at each block (H4), capacity and type (H5, room needs) ----
    def room_free(r, b):
        return not any(bg["room"] == r["room"] and overlaps(b["days"], b["s"], b["e"], bg["days"], bg["s"], bg["e"])
                       for bg in background)
    free = {(r["room"], b["block"]): room_free(r, b) for r in rooms for b in blocks}
    lab_need = {}
    for p in intake["instructors"]:
        for n in p.get("room_needs", []):
            if n.get("hard") and n.get("room_type") == "lab":
                lab_need[n["course"]] = True

    room_choices = int(os.environ.get("WILSON_ROOM_CHOICES", 4))
    def rooms_for(u, b):
        """The smallest few free rooms that fit. Larger rooms add search, not better schedules."""
        need_lab = u["room_need"] == "lab" or any(lab_need.get(c) for c in u["courses"])
        fit = [r for r in rooms if free[(r["room"], b["block"])] and r["capacity"] >= u["cap"]
               and ((r["type"] == "lab") == need_lab)]
        return sorted(fit, key=lambda r: (r["capacity"], r["room"]))[:room_choices]

    def available(name, b):
        return not any(in_window(b, w) for w in people[name]["unavailable"])

    def qualified(name, u):
        return any(c in people[name]["qualified"] for c in u["courses"])

    m = cp_model.CpModel()
    x = {}  # (unit, person, block, room) -> bool
    for u in placed:
        for name in people:
            if not qualified(name, u):
                continue
            for b in legal_blocks(u):
                if not available(name, b):
                    continue
                for r in rooms_for(u, b):
                    x[(u["id"], name, b["block"], r["room"])] = m.NewBoolVar("")
    y = {(u["id"], name): m.NewBoolVar("") for u in online for name in people if qualified(name, u)}
    miss = {u["id"]: m.NewBoolVar("") for u in placed + online}

    by_unit = defaultdict(list)
    for k, v in x.items():
        by_unit[k[0]].append(v)
    for k, v in y.items():
        by_unit[k[0]].append(v)
    for u in placed + online:
        m.Add(sum(by_unit[u["id"]]) + miss[u["id"]] == 1)

    # Symmetry breaking: sections of one course are interchangeable, so number them
    # in block order (in-person) or instructor order (online). Ties are allowed.
    border = {b["block"]: i + 1 for i, b in enumerate(blocks)}
    porder = {name: i + 1 for i, name in enumerate(people)}
    def ordered(group, key_of):
        keys = []
        for u in group:
            k = m.NewIntVar(0, 1000, "")
            m.Add(k == sum(key_of(kk) * v for kk, v in list(x.items()) + list(y.items()) if kk[0] == u["id"]))
            keys.append(k)
        for a, b in zip(keys, keys[1:]):
            m.Add(a <= b)
    same = defaultdict(list)
    for u in placed:
        same[("p", u["id"].split("#")[0])].append(u)
    for u in online:
        same[("o", u["id"].split("#")[0])].append(u)
    for (kind, _), group in same.items():
        if len(group) > 1:
            ordered(group, (lambda kk: border[kk[2]]) if kind == "p" else (lambda kk: porder[kk[1]]))

    bmap = {b["block"]: b for b in blocks}
    # time points: any two overlapping meetings share the later start (day, minute)
    points = sorted({(d, b["s"]) for b in blocks for d in b["days"]})
    active = {pt: [b["block"] for b in blocks if pt[0] in b["days"] and b["s"] <= pt[1] < b["e"]] for pt in points}

    per_person_block = defaultdict(list)
    per_room_block = defaultdict(list)
    per_person_block_room = defaultdict(list)
    per_course_block = defaultdict(list)
    for (uid, name, bid, rid), v in x.items():
        per_person_block[(name, bid)].append(v)
        per_room_block[(rid, bid)].append(v)
        per_person_block_room[(name, bid, rid)].append(v)
        per_course_block[(uid.split("#")[0], bid)].append(v)
    unit_by_id = {u["id"]: u for u in units}
    for pt, bids in active.items():
        for name in people:  # H3
            vs = [v for bid in bids for v in per_person_block.get((name, bid), [])]
            if len(vs) > 1:
                m.Add(sum(vs) <= 1)
        for r in rooms:  # H4
            vs = [v for bid in bids for v in per_room_block.get((r["room"], bid), [])]
            if len(vs) > 1:
                m.Add(sum(vs) <= 1)

    # H11 load: full-time may go one over, flagged as an overload; adjuncts may not.
    load_expr, over, under = {}, {}, {}
    for name, p in people.items():
        vs = [v for k, v in x.items() if k[1] == name] + [v for k, v in y.items() if k[1] == name]
        load_expr[name] = sum(vs)
        if p["status"] == "full-time":
            over[name] = m.NewIntVar(0, 1, "")
            under[name] = m.NewIntVar(0, p["load"], "")
            m.Add(load_expr[name] <= p["load"] + over[name])
            m.Add(load_expr[name] + under[name] >= p["load"])
        else:
            m.Add(load_expr[name] <= p["load"])

    # ---- objective ----
    terms = []
    def rank_score(name, u):
        rk = [people[name]["ranks"][c] for c in u["courses"] if c in people[name]["ranks"]]
        if not rk:
            return 0
        return W["S1_rank"].get(str(min(rk)), W["S1_rank"]["other"])

    for (uid, name, bid, rid), v in x.items():
        u = unit_by_id[uid]
        b, p = bmap[bid], people[name]
        s = rank_score(name, u)
        s += W["S2_prefer"] * max((inside_window(b, w) for w in p["prefer"]), default=0)
        if any(in_window(b, w) for w in p["avoid"]):
            s -= W["S2_avoid"]
        if not p["prefer"]:
            s += W["S3_habit"] * p["habit"][daypart(b["s"])]
        if u["level"] == "undergraduate" and "F" in b["days"] and b["s"] >= 13 * 60:
            s -= W["S8_friday_afternoon"]
        if p["status"] == "adjunct":
            s -= W["adjunct_section"]
        terms.append(round(s * SCALE) * v)
    for (uid, name), v in y.items():
        u = unit_by_id[uid]
        s = rank_score(name, u) - (W["adjunct_section"] if people[name]["status"] == "adjunct" else 0)
        terms.append(round(s * SCALE) * v)
    for v in miss.values():
        terms.append(-W["unassigned_section"] * SCALE * v)
    # Under-load rises per missing section (5, 10, 15...), so a shortfall spreads across
    # people instead of stacking on one. (Run 2026-11-05_run-03 put 2 of 4 on one person.)
    for name in over:
        terms.append(-W["S10_overload"] * SCALE * over[name])
        steps = [m.NewBoolVar("") for _ in range(people[name]["load"])]
        m.Add(under[name] == sum(steps))
        for a, b in zip(steps, steps[1:]):
            m.Add(a >= b)
        for k, s in enumerate(steps, 1):
            terms.append(-W["S10_underload"] * k * SCALE * s)

    # S4: sections of one multi-section course sharing a block
    spread = {}
    multi = {c["course"] for c in courses if c["in_person"] >= 3}
    for c in multi:
        for b in blocks:
            vs = per_course_block.get((c, b["block"]), [])
            if len(vs) > 1:
                ex = m.NewIntVar(0, len(vs), "")
                m.Add(ex >= sum(vs) - 1)
                spread[(c, b["block"])] = ex
                terms.append(-W["S4_same_block"] * SCALE * ex)

    # S5 and S6: consecutive blocks on the same days
    def consecutive(a, b):
        return a["days"] == b["days"] and 0 < b["s"] - a["e"] <= 20
    pairs = [(a, b) for a in blocks for b in blocks if consecutive(a, b)]
    triples = [(a, b, c) for a, b in pairs for b2, c in pairs if b2["block"] == b["block"]]
    uses = {(name, bid): sum(vs) for (name, bid), vs in per_person_block.items()}
    same_room_bonus, three_in_a_row = {}, {}
    for name, p in people.items():
        wt = W["S5_same_room_consecutive"] + (W["S5_requested_bonus"] if p["same_room"] else 0)
        for a, b in pairs:
            for r in rooms:
                va = per_person_block_room.get((name, a["block"], r["room"]))
                vb = per_person_block_room.get((name, b["block"], r["room"]))
                if va and vb:
                    both = m.NewBoolVar("")
                    m.Add(both <= sum(va))
                    m.Add(both <= sum(vb))
                    same_room_bonus[(name, a["block"], b["block"], r["room"])] = both
                    terms.append(round(wt * SCALE) * both)
        if not p["b2b2b_ok"]:
            for a, b, c in triples:
                if all((name, z["block"]) in uses for z in (a, b, c)):
                    t = m.NewBoolVar("")
                    m.Add(t >= uses[(name, a["block"])] + uses[(name, b["block"])] + uses[(name, c["block"])] - 2)
                    three_in_a_row[(name, a["block"], b["block"], c["block"])] = t
                    terms.append(-W["S6_three_in_a_row"] * SCALE * t)

    # Stability: start from the baseline run and reward keeping its placements.
    was, was_online = set(), set()
    if baseline:
        prev = list(csv.DictReader(open(Path(baseline) / "schedule.csv", encoding="utf-8")))
        was = {(r["unit"].split("#")[0], r["instructor"], r["block"]) for r in prev if r["mode"] == "in-person"}
        was_online = {(r["unit"].split("#")[0], r["instructor"]) for r in prev if r["mode"] == "online"}
        for (uid, name, bid, rid), v in x.items():
            if (uid.split("#")[0], name, bid) in was:
                terms.append(W["stability"] * SCALE * v)
        for (uid, name), v in y.items():
            if (uid.split("#")[0], name) in was_online:
                terms.append(W["stability"] * SCALE * v)
        by_course = defaultdict(list)
        for r in prev:
            if r["mode"] == "in-person":
                by_course[r["unit"].split("#")[0]].append(r)
        for course, rs in by_course.items():
            units_here = sorted((u for u in placed if u["id"].split("#")[0] == course), key=lambda u: int(u["id"].split("#")[1]))
            rs.sort(key=lambda r: border.get(r["block"], 0))
            for u, r in zip(units_here, rs):
                k = (u["id"], r["instructor"], r["block"], r["room"])
                if k in x:
                    m.AddHint(x[k], 1)

    m.Maximize(sum(terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(os.environ.get("WILSON_SOLVE_SECONDS", 30))
    solver.parameters.num_workers = 8
    solver.parameters.random_seed = 7
    status = solver.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        sys.exit(f"solver status {solver.StatusName(status)}")

    # ---- write the schedule ----
    out = []
    for (uid, name, bid, rid), v in x.items():
        if solver.Value(v):
            u, b = next(z for z in placed if z["id"] == uid), bmap[bid]
            out.append({"unit": uid, "courses": "/".join(u["courses"]), "title": u["title"], "level": u["level"],
                        "mode": "in-person", "instructor": name, "block": bid, "days": b["days"],
                        "start": b["start"], "end": b["end"], "room": rid, "cap": u["cap"]})
    for (uid, name), v in y.items():
        if solver.Value(v):
            u = next(z for z in online if z["id"] == uid)
            out.append({"unit": uid, "courses": "/".join(u["courses"]), "title": u["title"], "level": u["level"],
                        "mode": "online", "instructor": name, "block": "", "days": "", "start": "", "end": "",
                        "room": "", "cap": u["cap"]})
    for u in arranged:
        out.append({"unit": u["id"], "courses": "/".join(u["courses"]), "title": u["title"], "level": u["level"],
                    "mode": "arranged", "instructor": "TBD by chair", "block": "", "days": "", "start": "",
                    "end": "", "room": "", "cap": u["cap"]})
    unassigned = [uid for uid, v in miss.items() if solver.Value(v)]
    for uid in unassigned:
        u = next(z for z in placed + online if z["id"] == uid)
        out.append({"unit": uid, "courses": "/".join(u["courses"]), "title": u["title"], "level": u["level"],
                    "mode": "UNASSIGNED", "instructor": "", "block": "", "days": "", "start": "", "end": "",
                    "room": "", "cap": u["cap"]})
    out.sort(key=lambda r: (r["courses"], r["mode"], r["days"], r["start"]))
    cols = ["unit", "courses", "title", "level", "mode", "instructor", "block", "days", "start", "end", "room", "cap"]
    with open(run / "schedule.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)

    # ---- explain: per-person outcomes the reviewer reads ----
    per = {}
    for name, p in people.items():
        mine = [r for r in out if r["instructor"] == name]
        got = {c for r in mine for c in r["courses"].split("/")}
        per[name] = {
            "status": p["status"], "answered_survey": p["answered"], "load_target": p["load"],
            "assigned": len(mine), "overload": bool(over.get(name) is not None and solver.Value(over[name])),
            "under_load_by": solver.Value(under[name]) if name in under else 0,
            "ranked_courses": p["ranks"],
            "ranked_courses_not_given": sorted(c for c in p["ranks"] if c not in got),
            "sections": [f"{r['courses']} {r['days']} {r['start']}-{r['end']} {r['room']}".strip() for r in mine],
            "prefer_windows": p["prefer"],
            "prefer_met": [r["unit"] for r in mine if r["block"] and max((inside_window(bmap[r["block"]], w) for w in p["prefer"]), default=0) >= 0.5],
            "avoid_hit": [r["unit"] for r in mine if r["block"] and any(in_window(bmap[r["block"]], w) for w in p["avoid"])],
        }
    log = {
        "status": solver.StatusName(status), "objective": solver.ObjectiveValue() / SCALE,
        "wall_seconds": round(solver.WallTime(), 1), "variables": len(x) + len(y),
        "baseline": str(baseline) if baseline else None,
        "kept_from_baseline": (f"{sum(1 for r in out if (r['unit'].split('#')[0], r['instructor'], r['block']) in was or (r['unit'].split('#')[0], r['instructor']) in was_online)} of {len(was) + len(was_online)}" if baseline else None),
        "units": {"in_person": len(placed), "online": len(online), "arranged": len(arranged)},
        "unassigned": unassigned,
        "blocks_removed_for_commons_hour": commons_blocked,
        "same_block_collisions": {f"{c} {bid}": solver.Value(v) + 1 for (c, bid), v in spread.items() if solver.Value(v)},
        "same_room_consecutive_pairs": [f"{n}: {a}->{b} in {r}" for (n, a, b, r), v in same_room_bonus.items() if solver.Value(v)],
        "three_in_a_row": [f"{n}: {a}->{b}->{c}" for (n, a, b, c), v in three_in_a_row.items() if solver.Value(v)],
        "people": per,
    }
    (run / "solver-log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"{log['status']} in {log['wall_seconds']}s | {len(out)} rows | unassigned {len(unassigned)} | "
          f"objective {log['objective']}")


if __name__ == "__main__":
    args = sys.argv[1:]
    base = args[args.index("--baseline") + 1] if "--baseline" in args else None
    main(args[0], base)
