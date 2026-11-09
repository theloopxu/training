# Wilson scheduler

A fictional faculty-scheduling exercise for The Loop Agentic AI Literacy class. These files are teaching data, not an operational Xavier schedule.

## Start in Claude Cowork

1. Extract this folder onto your Desktop and give Cowork access to it.
2. Ask: "Read CLAUDE.md first and follow it. Check the required packages in your execution environment. Explain the workflow and where you will stop for my input. Do not run the schedule yet."
3. Ask: "Run the schedule using survey/responses-fall-2027.xlsx."
4. Review the open questions. Answer them or say "Use defaults."
5. Open the reported schedule.html file in your browser.
6. Start a new Cowork session with the same folder and ask: "Read CLAUDE.md and agents/reviewer.md. Review the latest completed scheduling run."

Python packages are needed in the agent's execution environment, not necessarily on your own computer. The agent checks them and can install from requirements.txt if its network and account settings permit it. If installation fails, stop and show the instructor the error.

## Files

CLAUDE.md defines the workflow. agents/ contains intake and reviewer roles. survey/ holds the sample preferences. school/ and constraints/ hold reference data and rules. tools/ holds the deterministic validator, solver, checker and renderer. Each attempt writes into a new runs/ folder. learnings.md records lessons after review.

Inputs remain read-only. Do not overwrite an earlier run. Review output before using it. A passing conflict check does not establish that every preference or institutional priority has been satisfied.

The spreadsheet and CSV contain the same sample survey. The classroom exercise names the spreadsheet explicitly so file timestamps do not choose between them.
