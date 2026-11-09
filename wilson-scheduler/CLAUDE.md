# Wilson scheduler

This folder is an agent. It builds the Fall 2027 class schedule for the Management department of Wilson College of Business, a fictional school.

- **The problem:** a department chair builds about 40 sections a term by hand from a faculty preference survey.
- **Input:** the newest survey file in `survey/`.
- **Output:** a run folder in `runs/` with a schedule that breaks no hard rule, an explanation for the chair, and a page to open.

## Read first, in order

1. This file.
2. `constraints/rules.md`: the hard and soft rules.
3. `school/college.md`: the college, its rooms and the department.
4. `learnings.md`: what earlier runs taught.

## Folder map

| Path | Holds | Who may change it |
|---|---|---|
| `CLAUDE.md` | These instructions | The human |
| `agents/` | Two roles: `intake.md` and `reviewer.md` | The human |
| `survey/` | Input: faculty survey exports, newest one wins | The human drops files here |
| `school/` | Reference: courses, faculty, rooms, time grid, other departments' sections | Nobody |
| `constraints/` | Reference: `rules.md` and solver weights in `weights.json` | The human, after a run teaches something |
| `tools/` | Scripts for the exact work: validate, solve, check, render | The human |
| `runs/` | Output: one folder per run, `YYYY-MM-DD_run-NN` | This agent, inside the current run only |
| `learnings.md` | One dated entry per run | This agent, at the end of a run |

## Before the first run in a session

Commands run in a sandbox with `python3`. Check the two required packages:

```
python3 -c "import ortools, openpyxl"
```

If either import fails, run `python3 -m pip install -r requirements.txt`. If the install fails, stop and report the exact error. Network restrictions or package compatibility may require instructor help. Do not change organization settings.

## How a run works

The trigger is "Run the schedule." The human may name a survey file. Otherwise use the newest file in `survey/`.

| Step | Who | Does | Writes |
|---|---|---|---|
| 1 | You | Create the next free `runs/YYYY-MM-DD_run-NN/` | The run folder |
| 2 | You, as intake | Read `agents/intake.md` and follow it exactly | `intake.json`, `intake.md` |
| 3 | `tools/validate_intake.py` | Check the intake | Pass, or errors to fix |
| 4 | The human | Answers the open questions, or says "use defaults." Stop and wait here. | Your record of the answers in `intake.json`, quoting the human |
| 5 | `tools/run_tools.py` | Solve, check and render in one step | `schedule.csv`, `solver-log.json`, `check.md`, `schedule.html` |
| 6 | You | Report pass or fail, sections placed, decisions left for the chair, and the path to `schedule.html` | Nothing |
| 7 | A new session, as reviewer | The human starts a new session in this project and sends "Review the latest run." That session reads `agents/reviewer.md` and follows it. | `review.md` |
| 8 | The reviewing session | Run `tools/render.py` again so the page includes the review, then add the run's entry to `learnings.md` | `schedule.html`, `learnings.md` |

If `check.md` says FAIL at step 5, stop and show it to the human.

Commands, from this folder:

```
python3 tools/validate_intake.py runs/<run>
python3 tools/run_tools.py runs/<run>
python3 tools/render.py runs/<run>
```

**After one answer changes.** When the human changes a survey answer, start a new run with the previous run as the baseline. It moves only what the change forces and finishes in seconds. Report which sections moved and why.

```
python3 tools/run_tools.py runs/<new> --baseline runs/<previous>
```

After a change to `tools/` or `weights.json`, solve fresh with no baseline. The solver's time limit defaults to 30 seconds; set `WILSON_SOLVE_SECONDS` to change it.

## Rules of the house

- **Inputs are read-only.** Write only inside the current run folder and `learnings.md`.
- **Scripts decide what must be certain.** Placement, conflict checking and rendering are code. You interpret free text and explain tradeoffs.
- **The maker never checks its own work.** The solver places, `check.py` verifies, and a separate session reviews.
- **Quote or don't claim.** Every rule taken from the survey quotes the answer. Every review claim cites a file.
- **Unknowns become questions.** If the data cannot answer it, ask and state the default. Never guess.
- **A human approves.** The schedule is a draft for the chair. Never send, email or publish anything.
- **You cannot open files on the human's computer.** Give the path to `schedule.html`; the human double-clicks it.

## Definition of done

A run is done when `check.md` says PASS, `review.md` exists, `schedule.html` shows the review, and `learnings.md` has the run's entry.
