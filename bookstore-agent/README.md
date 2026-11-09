# Bookstore agent: ready-to-run teaching case

This is a complete fictional customer-service agent for The Loop Agentic AI Literacy class. It contains five sample emails, an order table and a finished policy. Students do not need to edit Markdown or install packages before running it.

## Set up

1. Download [bookstore-agent.zip](https://github.com/theloopxu/training/raw/refs/heads/main/downloads/bookstore-agent.zip) in your browser. It normally saves to Downloads.
2. In a setup Cowork session, connect Downloads and Desktop. Ask Claude to extract the bookstore-agent folder onto Desktop without overwriting anything. The ZIP already contains one bookstore-agent/ folder; avoid nesting it inside a second folder with the same name.
3. Create a Bookstore Agent project using the extracted folder as context. Add this project instruction: "Read CLAUDE.md in the connected bookstore-agent folder before each task and follow it."
4. Ask "How does this agent work? Don't run it yet."
5. When ready, say "Process the inbox." No edits to the supplied files are required.
6. Inspect outputs/run-001/SUMMARY.md and the five draft replies. Later runs use the next unused number.

Cowork needs read/write access to the extracted folder and enough usage allowance to finish the task. No external connectors, web access or additional packages are required for the exercise itself. Completion time depends on the model and account. If file access fails, stop and reconnect the folder.

## What happens

The agent matches each email to the order table, applies the supplied fictional policy, writes a draft and records decisions requiring human review. It never sends mail or performs transactions. The sample dates stay in 2026; the policy uses the date of each customer email so the exercise works later too.

inbox/ and reference/ stay unchanged. outputs/ starts empty and receives one folder per run. CLAUDE.md contains the job instructions. This simple agent has no separate roles, tools or memory files: its instructions and reference files are enough for the exercise.

## Attribution

Adapted from Jaisen Mathai's MGMT 342 Session 13 exercise. See SOURCES.md. This version supplies the instructions and fictional policy rather than asking students to write them. It is not an official bookstore policy, and draft replies must not be sent to the sample addresses.
