"""
Render a run as one self-contained HTML page: week view, by instructor, by room,
the hard-rule check and the reviewer's notes (if review.md exists yet).

  python tools/render.py runs/2026-11-05_run-01
"""
import csv
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from common import hhmm, load_school, mins

KIND_COLOR = {"core": "var(--s1)", "elective": "var(--s3)", "graduate": "var(--s7)"}
BULLET, NUMBERED = r"^\s*[-*] ", r"^\d+\. "
DAYS = [("M", "Mon"), ("T", "Tue"), ("W", "Wed"), ("R", "Thu"), ("F", "Fri")]


def md(text):
    """Small markdown subset: headings, bullets, tables, bold, code."""
    out, table = [], []
    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        return re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    def flush():
        if table:
            rows = [r for r in table if not re.match(r"^\|\s*:?-", r)]
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells[0]) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in cells[1:]) + "</tbody></table>")
            table.clear()
    for line in text.splitlines():
        if line.startswith("|"):
            table.append(line)
            continue
        flush()
        if line.startswith("#"):
            n = min(len(line) - len(line.lstrip("#")) + 1, 4)
            out.append(f"<h{n}>{inline(line.lstrip('#').strip())}</h{n}>")
        elif re.match(BULLET, line):
            out.append("<li>" + inline(re.sub(BULLET, "", line)) + "</li>")
        elif re.match(NUMBERED, line):
            out.append("<li>" + inline(re.sub(NUMBERED, "", line)) + "</li>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    flush()
    return "\n".join(out)


def main(run):
    run = Path(run)
    blocks, rooms, background, courses, faculty = load_school()
    sched = list(csv.DictReader(open(run / "schedule.csv", encoding="utf-8")))
    log = json.loads((run / "solver-log.json").read_text(encoding="utf-8"))
    check = (run / "check.md").read_text(encoding="utf-8") if (run / "check.md").exists() else "Not checked yet."
    review = (run / "review.md").read_text(encoding="utf-8") if (run / "review.md").exists() else ""
    core = {c["course"] for c in courses if c["in_person"] >= 3}

    def kind(r):
        if r["level"] == "graduate":
            return "graduate"
        return "core" if r["courses"] in core else "elective"

    timed = [r for r in sched if r["mode"] == "in-person"]
    passed = "PASS" in check
    day0, day1, H = 8 * 60, 21 * 60, 640
    y = lambda m: 24 + (H - 30) * (m - day0) / (day1 - day0)  # noqa: E731
    W, L = 1000, 48
    cw = (W - L) / 5
    svg = []
    for h in range(8, 22):
        svg.append(f'<line x1="{L}" x2="{W}" y1="{y(h*60):.1f}" y2="{y(h*60):.1f}" stroke="var(--grid)"/>'
                   f'<text x="{L-6}" y="{y(h*60)+4:.1f}" text-anchor="end">{hhmm(h*60)}</text>')
    for i, (_, name) in enumerate(DAYS):
        svg.append(f'<text x="{L + i*cw + cw/2:.0f}" y="14" text-anchor="middle">{name}</text>')
    # lanes so overlapping sections sit side by side
    for i, (d, _) in enumerate(DAYS):
        today = sorted([r for r in timed if d in r["days"]], key=lambda r: (mins(r["start"]), r["unit"]))
        lanes = []
        placed = []
        for r in today:
            s, e = mins(r["start"]), mins(r["end"])
            lane = next((k for k, end in enumerate(lanes) if end <= s), None)
            if lane is None:
                lanes.append(e); lane = len(lanes) - 1
            else:
                lanes[lane] = e
            placed.append((r, lane))
        n = max(len(lanes), 1)
        lw = (cw - 4) / n
        for r, lane in placed:
            s, e = mins(r["start"]), mins(r["end"])
            x0 = L + i * cw + 2 + lane * lw
            tip = html.escape(f"{r['courses']} {r['title']} | {r['instructor']} | {hhmm(s)}-{hhmm(e)} | {r['room']} | cap {r['cap']}")
            svg.append(f'<g><title>{tip}</title><rect x="{x0+1:.1f}" y="{y(s)+1:.1f}" width="{lw-2:.1f}" height="{y(e)-y(s)-2:.1f}" rx="3" fill="{KIND_COLOR[kind(r)]}"/>'
                       + (f'<text x="{x0+4:.1f}" y="{y(s)+13:.1f}" class="lbl">{html.escape(r["courses"].split("/")[0].replace(" ", ""))}</text>' if lw > 34 else "") + "</g>")
    week = f'<svg viewBox="0 0 {W} {H}" role="img">{"".join(svg)}</svg>'

    def row(r, where="room"):
        when = f"{r['days']} {hhmm(mins(r['start']))}-{hhmm(mins(r['end']))}" if r["start"] else r["mode"]
        return f"<tr><td>{html.escape(r['courses'])}</td><td>{html.escape(r['title'])}</td><td>{when}</td><td>{html.escape(r[where])}</td><td class=n>{r['cap']}</td></tr>"

    people = defaultdict(list)
    for r in sched:
        people[r["instructor"] or "(unassigned)"].append(r)
    by_person = []
    for name in sorted(people, key=lambda n: (n.startswith("TBD"), n)):
        info = log["people"].get(name, {})
        meta = (f"{info.get('assigned', len(people[name]))} of {info.get('load_target', '?')} sections"
                + (" · <b>overload</b>" if info.get("overload") else "")
                + (f" · missed ranked: {', '.join(info['ranked_courses_not_given'])}" if info.get("ranked_courses_not_given") else ""))
        by_person.append(f"<details><summary><b>{html.escape(name)}</b> <span class=muted>{meta}</span></summary>"
                         f"<table><tbody>{''.join(row(r) for r in sorted(people[name], key=lambda r: (r['days'], r['start'])))}</tbody></table></details>")

    rooms_used = defaultdict(list)
    for r in timed:
        rooms_used[r["room"]].append(r)
    by_room = "".join(f"<details><summary><b>{html.escape(k)}</b> <span class=muted>{len(v)} sections</span></summary><table><tbody>"
                      f"{''.join(row(r, 'instructor') for r in sorted(v, key=lambda r: (r['days'], r['start'])))}</tbody></table></details>"
                      for k, v in sorted(rooms_used.items()))
    unassigned = [r for r in sched if r["mode"] == "UNASSIGNED"]
    online = [r for r in sched if r["mode"] in ("online", "arranged")]

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wilson Management Schedule</title>
<style>
:root{{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--ring:rgba(11,11,11,.1);--navy:#0c2340;--s1:#2a78d6;--s3:#1baf7a;--s7:#6250d6;--ok:#006300;--bad:#d03b3b}}
@media (prefers-color-scheme:dark){{:root:where(:not([data-theme=light])){{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--ring:rgba(255,255,255,.1);--navy:#9ec5f4;--s1:#3987e5;--s3:#199e70;--s7:#9085e9;--ok:#0ca30c;--bad:#e66767}}}}
:root[data-theme=dark]{{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--ring:rgba(255,255,255,.1);--navy:#9ec5f4;--s1:#3987e5;--s3:#199e70;--s7:#9085e9;--ok:#0ca30c;--bad:#e66767}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--page);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:20px 16px 48px}}h1{{margin:0;color:var(--navy);font-size:22px}}h2{{font-size:16px;margin:0 0 8px}}
.sub{{color:var(--ink2);margin:4px 0 16px}}.card{{background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:14px 16px;margin-bottom:16px;overflow-x:auto}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}}.kpi{{background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:12px}}
.kpi b{{display:block;font-size:22px}}.kpi span{{color:var(--muted);font-size:12px}}svg{{width:100%;height:auto;display:block}}svg text{{fill:var(--muted);font-size:11px}}svg text.lbl{{fill:#fff;font-size:10px}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0}}th,td{{text-align:left;padding:4px 8px;border-bottom:1px solid var(--grid)}}td.n{{text-align:right}}
details{{border-bottom:1px solid var(--grid);padding:6px 0}}summary{{cursor:pointer}}.muted{{color:var(--muted);font-size:12px}}
.legend{{display:flex;gap:14px;font-size:12px;color:var(--ink2);margin-top:6px}}.legend i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}}
.pass{{color:var(--ok);font-weight:700}}.fail{{color:var(--bad);font-weight:700}}.review h2,.review h3{{margin-top:14px}}code{{font-size:12px}}
</style></head><body><main>
<h1>Wilson College of Business · Management · Fall 2027</h1>
<p class="sub">Draft schedule from run <code>{html.escape(run.name)}</code>. For the chair's review. Fictional school; every name is invented.</p>
<div class="kpis">
<div class="kpi"><b class="{'pass' if passed else 'fail'}">{'PASS' if passed else 'FAIL'}</b><span>Hard-rule check</span></div>
<div class="kpi"><b>{len(timed)}</b><span>In-person sections placed</span></div>
<div class="kpi"><b>{len(online)}</b><span>Online or arranged</span></div>
<div class="kpi"><b>{len(unassigned)}</b><span>Left for the chair</span></div>
<div class="kpi"><b>{log['wall_seconds']}s</b><span>Solver time</span></div>
</div>
<div class="card"><h2>The week</h2>{week}
<div class="legend"><span><i style="background:var(--s1)"></i>Core (multi-section)</span><span><i style="background:var(--s3)"></i>Elective</span><span><i style="background:var(--s7)"></i>Graduate</span></div>
<p class="muted">Hover a block for course, instructor, time and room.</p></div>
{f'<div class="card review"><h2>Reviewer notes</h2>{md(review)}</div>' if review else ''}
<div class="card"><h2>By instructor</h2>{''.join(by_person)}</div>
<div class="card"><h2>By room</h2>{by_room}</div>
<div class="card"><h2>Hard-rule check</h2>{md(check)}</div>
</main></body></html>"""
    (run / "schedule.html").write_text(page, encoding="utf-8")
    print(f"wrote {run / 'schedule.html'}")


if __name__ == "__main__":
    main(sys.argv[1])
