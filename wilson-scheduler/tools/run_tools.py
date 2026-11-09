"""
Run the deterministic half of a run in order: solve, check, render.
Stops at the first failure. Intake and review are agent steps, not here.

  python tools/run_tools.py runs/2026-11-05_run-01
  python tools/run_tools.py runs/2026-11-05_run-02 --baseline runs/2026-11-05_run-01
"""
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def main(run, baseline=None):
    for step in ("validate_intake.py", "solve.py", "check.py", "render.py"):
        print(f"== {step}", flush=True)
        extra = ["--baseline", baseline] if step == "solve.py" and baseline else []
        if subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / step), run, *extra], cwd=TOOLS).returncode:
            sys.exit(f"stopped at {step}")


if __name__ == "__main__":
    args = sys.argv[1:]
    base = str(Path(args[args.index("--baseline") + 1]).resolve()) if "--baseline" in args else None
    main(str(Path(args[0]).resolve()), base)
