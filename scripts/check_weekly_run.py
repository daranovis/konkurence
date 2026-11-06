"""Zjistí, jestli proběhla týdenní kontrola konkurence za aktuální týden.

Týdenní běh je naplánovaný na pondělí 10:00 (cloud rutina). Skript najde poslední takový termín
<= teď a hledá report reports/weekly/YYYY-MM-DD.md s datem v tom týdnu (po–ne),
na GitHubu (origin/main) i lokálně.

Použití:
    python scripts/check_weekly_run.py [--now 2026-11-10T09:00] [--no-fetch]

Výstup: jeden řádek JSON. Exit code:
    0 = ok (report existuje), not_due (první běh ještě nebyl na řadě) nebo pending (cloud běh možná ještě běží)
    1 = missing (report chybí, je potřeba kontrolu spustit)
    2 = chyba
"""
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_WEEKDAY, RUN_HOUR = 0, 10          # pondělí 10:00 místního času (Europe/Prague)
GRACE = dt.timedelta(hours=2)           # čas pro doběhnutí cloud rutiny
FIRST_RUN = dt.date(2026, 11, 9)        # první naplánovaný týdenní běh
REPORT_RE = re.compile(r"reports/weekly/(\d{4}-\d{2}-\d{2})\.md$")


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8")


def report_dates(fetch: bool):
    dates, source = set(), []
    if fetch:
        f = git("fetch", "-q", "origin")
        source.append("origin" if f.returncode == 0 else "origin(fetch selhal, použita poslední známá verze)")
    r = git("ls-tree", "-r", "--name-only", "origin/main", "reports/weekly/")
    if r.returncode == 0:
        dates |= {m.group(1) for line in r.stdout.splitlines() if (m := REPORT_RE.search(line))}
    local = ROOT / "reports" / "weekly"
    if local.exists():
        dates |= {p.stem for p in local.glob("*.md") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)}
        source.append("lokální")
    return dates, source


def main():
    args = sys.argv[1:]
    now = dt.datetime.fromisoformat(args[args.index("--now") + 1]) if "--now" in args else dt.datetime.now()
    days_back = (now.weekday() - RUN_WEEKDAY) % 7
    scheduled = (now - dt.timedelta(days=days_back)).replace(hour=RUN_HOUR, minute=0, second=0, microsecond=0)
    if scheduled > now:
        scheduled -= dt.timedelta(days=7)
    week_start = scheduled.date()
    week_end = week_start + dt.timedelta(days=6)

    out = {"now": now.isoformat(timespec="minutes"), "week": f"{week_start}..{week_end}"}
    if week_start < FIRST_RUN:
        out.update(status="not_due", message=f"První týdenní běh je až {FIRST_RUN}.")
        print(json.dumps(out, ensure_ascii=False)); sys.exit(0)

    try:
        dates, source = report_dates(fetch="--no-fetch" not in args)
    except Exception as exc:  # noqa: BLE001
        out.update(status="error", message=str(exc))
        print(json.dumps(out, ensure_ascii=False)); sys.exit(2)

    found = sorted(d for d in dates if str(week_start) <= d <= str(week_end))
    out["checked"] = source
    if found:
        out.update(status="ok", found=found, message=f"Report za týden existuje: {', '.join(found)}.")
        code = 0
    elif now < scheduled + GRACE:
        out.update(status="pending", message="Report zatím není, ale cloud rutina může ještě běžet.")
        code = 0
    else:
        out.update(status="missing", message=f"Report za týden {week_start}–{week_end} chybí. Spusť kontrolu konkurence.")
        code = 1
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(code)


if __name__ == "__main__":
    main()
