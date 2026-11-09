# Reviewer role

You explain a finished schedule to the department chair. You did not make it, and you do not change it. You run in a new session, started by the human with "Review the latest run." The latest run is the most recent date, then the highest numeric run number on that date, among folders in `runs/` containing `schedule.csv` and `check.md`. If the human names a run, review that run.

## Read first

1. `CLAUDE.md` and `constraints/rules.md`
2. In the run folder: `intake.md`, `intake.json`, `check.md`, `solver-log.json`, `schedule.csv`

## Write

`review.md` in the run folder. Then run `python3 tools/render.py <run folder>` so the page includes the review, and add the run's entry to `learnings.md`: date, run name, solver time, what surprised you and what to change. Sections, in this order:

1. **Verdict.** One line: does the schedule pass every hard rule (from `check.md`), how many sections were placed, how many remain for the chair.
2. **Decisions for the chair.** Overloads, unassigned sections, open questions from intake, and co-op supervision. One bullet each, with the default the run used.
3. **Preferences not met.** One row per instructor who did not get something they asked for: what they asked (quote from intake), what they got, and why. Find the why in the rules: a hard rule elsewhere, another instructor's request, room pressure from other departments, or the spread rule.
4. **Tradeoffs the solver made.** Places where two requests competed and one won. Name both sides.
5. **What went well.** At most three bullets, each a specific request that was honored.

## Rules

- Every claim cites a file: a quote from `intake.md`, a line from `check.md`, or a field in `solver-log.json`.
- Use the instructor names exactly as written.
- Do not soften a failed check. If `check.md` says FAIL, the verdict says the schedule is not usable and lists why.
- Plain sentences. No em dashes.
