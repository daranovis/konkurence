"""Vygeneruje čitelný seznam konkurentů `konkurenti.md` z `competitors.yaml` a posledních snapshotů.

Použití:  python scripts/build_competitor_list.py
Potřebuje PyYAML (pip install pyyaml).
"""
import datetime as dt
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TYPES = {"vlastni_krematorium": "vlastní pec", "pobocka": "pobočka / sběrné místo",
         "zprostredkovatel": "zprostředkovatel", "nezjisteno": "nezjištěno"}
PRIO = {"high": 0, "medium": 1, "low": 2}


def latest_snapshots():
    snap = ROOT / "data" / "snapshots"
    out = {}
    for d in sorted(p for p in snap.iterdir() if p.is_dir()):
        for f in d.glob("*.json"):
            out[f.stem] = json.loads(f.read_text(encoding="utf-8"))  # novější přepíše starší
    return out


def kc(v):
    return "–" if v in (None, "") else f"{int(v):,}".replace(",", " ")


def domain(url):
    return url.split("//")[-1].split("/")[0].removeprefix("www.")


def main():
    cfg = yaml.safe_load((ROOT / "competitors.yaml").read_text(encoding="utf-8"))
    snaps = latest_snapshots()
    comps = cfg.get("competitors") or []
    today = dt.date.today()

    def row(i, c):
        s = snaps.get(c["slug"], {})
        p = s.get("cremation_prices") or {}
        status = c.get("status") or ("bez snapshotu" if not s else "aktivní")
        return (f"| {i} | {c['name']} | [{domain(c['url'])}]({c['url']}) | {c.get('kraj', '')} | "
                f"{TYPES.get(c.get('type'), c.get('type', ''))} | {c.get('operator', '') or '–'} | {c.get('priority', '')} | "
                f"{kc(p.get('1-5'))} | {kc(p.get('10-20'))} | {c.get('added', '')} | {status} |")

    comps_sorted = sorted(comps, key=lambda c: (PRIO.get(c.get("priority"), 9), str(c.get("kraj")), c["name"]))
    recent = [c for c in comps if c.get("added") and (today - dt.date.fromisoformat(str(c["added"]))).days <= 30]

    mp = (snaps.get("memorypet") or {}).get("cremation_prices") or {}
    lines = [
        "# Seznam konkurentů Memory Pet",
        "",
        f"*Automaticky generováno z `competitors.yaml` ({today.isoformat()}). Needituj ručně, uprav YAML a spusť `python scripts/build_competitor_list.py`.*",
        "",
        f"Sledujeme **{len(comps)} subjektů**. Každý týden se hledají noví a hned se analyzují (skill `konkurence-check`, krok 0).",
        f"Pro srovnání Memory Pet: 1–5 kg **{kc(mp.get('1-5'))} Kč**, 10–20 kg **{kc(mp.get('10-20'))} Kč**.",
        "",
        "## Sledovaní konkurenti",
        "| # | Název | Web | Kraj | Typ | Síť / provozovatel | Priorita | 1–5 kg | 10–20 kg | Sledujeme od | Stav |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        *[row(i, c) for i, c in enumerate(comps_sorted, 1)],
        "",
        "## Přidáno za posledních 30 dní",
        *([f"- {c['added']}: **{c['name']}** ({c.get('kraj', '')}), nalezeno přes: {c.get('found_via', 'úvodní analýza')}" for c in sorted(recent, key=lambda c: str(c['added']), reverse=True)] or ["- nic"]),
    ]
    cands = cfg.get("candidates") or []
    if cands:
        lines += ["", "## Kandidáti (čekají na první analýzu)", *[f"- {c['name']}: {c['url']} ({c.get('kraj', '')})" for c in cands]]
    excl = cfg.get("excluded") or []
    lines += ["", "## Vyřazené (nalezené, ale nesledujeme)",
              *([f"- {c['name']}: {c.get('url', '')}, důvod: {c.get('reason', '')}" for c in excl] or ["- nic"])]
    (ROOT / "konkurenti.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"konkurenti.md: {len(comps)} konkurentů, {len(cands)} kandidátů, {len(excl)} vyřazených")


if __name__ == "__main__":
    main()
