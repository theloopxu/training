---
title: Wilson scheduling rules
created: 2026-11-05
derived_from: nine years of real section data from a business college, profiled and anonymized
---

# Wilson scheduling rules

Every rule the scheduler follows. Hard rules are never broken; `tools/check.py` rejects any schedule that breaks one. Soft rules are scored; their weights live in `weights.json`.

## Hard rules

| ID | Rule |
|---|---|
| H1 | An undergraduate in-person section uses a block in `school/grid.csv`. |
| H2 | A graduate in-person section uses a one-night evening block (6:00 to 8:30 p.m., Monday to Thursday). |
| H3 | No instructor teaches two overlapping sections. |
| H4 | No room holds two sections at once. Other departments' sections in `school/background-fall-2027.csv` count. |
| H5 | Room capacity is at least the section cap. |
| H6 | No section meets during Commons Hour, Monday 3:45 to 5:00 p.m. This removes the MW 4:30 block. |
| H7 | Cross-listed sections (ENTR 305 and MGMT 305) meet together: one block, one room, one instructor. |
| H8 | Capstones run in spring only. None are offered this fall. |
| H9 | No instructor teaches during a time they marked "can't teach", including "Other" answers. Adjuncts teach only blocks starting at 4:00 p.m. or later. |
| H10 | An instructor teaches only courses they listed on the survey or have taught before (`qualified` in `school/management-faculty.csv`). |
| H11 | A full-time instructor teaches at most their load, plus one section flagged as an overload for chair and dean approval. Adjuncts never exceed their load. A survey answer about releases sets the load. |
| Room need | A course with a stated lab need meets in the WH AI Lab. Nothing else meets there. |

## Soft rules

| ID | Rule |
|---|---|
| S1 | Give instructors their ranked course choices. |
| S2 | Honor time preferences stated in the free text. |
| S3 | When an instructor states no time preference, follow their usual time of day. |
| S4 | Spread sections of a multi-section course across different blocks. |
| S5 | Put one instructor's consecutive sections in the same room. Worth more when they asked for it. |
| S6 | Avoid three consecutive sections for one instructor, unless they said they are fine with it. |
| S8 | Avoid undergraduate sections starting Friday at 1:00 p.m. or later. |
| S10 | Keep full-time instructors at their load. Prefer an adjunct to an overload. Each further missing section costs more than the last, so a shortfall is shared. |

S7 and S9 from the source rule set are covered by H9 (adjunct evenings) and the room-need rule.

## What the scheduler cannot know

These are not in the data. The intake agent turns them into open questions, never guesses.

- Room features beyond capacity and the lab (movable tables, tiered seating, technology).
- Section counts other than the defaults in `school/management-courses.csv`.
- Who supervises co-op and internship sections. They are listed as "TBD by chair".
