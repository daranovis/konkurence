"""Vytvoří datové soubory pro dashboard ze snapshotů.

Výstup:
    data/dashboard/subjects.json  – jeden řádek na subjekt z nejnovějšího snapshotu
    data/dashboard/history.json   – ceny kremace ze všech snapshotů (datum × subjekt × kategorie)

Použití:
    python scripts/build_dashboard_data.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "data" / "snapshots"
OUT = ROOT / "data" / "dashboard"

CATS = ["0-1", "1-5", "5-10", "10-20", "20-40", "40-60", "60+"]
COLS = {"0-1": "p_0_1", "1-5": "p_1_5", "5-10": "p_5_10", "10-20": "p_10_20",
        "20-40": "p_20_40", "40-60": "p_40_60", "60+": "p_60"}
OWN = {"memorypet", "memorypetpoint"}
# Subjekty, které působí ve spádové oblasti Memory Pet (Liberecký, Ústecký,
# Královéhradecký, Karlovarský kraj, Praha a Střední Čechy).
REGION = {"memorypet", "memorypetpoint", "kz-praha", "kz-liberec", "kz-usti", "pet-pieta",
          "fatima", "kerberos", "vecna-loviste", "goodbye", "pet-heaven", "vitem"}
TYPE_LABEL = {"vlastni_krematorium": "vlastní pec", "pobocka": "pobočka",
              "zprostredkovatel": "zprostředkovatel", "nezjisteno": "nezjištěno"}


def texts(d, *keys):
    out = []
    for k in keys:
        for item in d.get(k) or []:
            out.append(json.dumps(item, ensure_ascii=False).lower() if isinstance(item, dict) else str(item).lower())
    return out


def video_free(d):
    """Videozáznam kremace zdarma: bonus nebo služba se slovem video/záznam a cenou 0 / „zdarma“."""
    for t in texts(d, "bonuses"):
        if ("video" in t or "záznam" in t) and "zdarma" in t:
            return True
    for s in d.get("services") or []:
        label = str(s.get("label", "")).lower()
        price = s.get("price")
        if ("video" in label or "záznam" in label) and (price == 0 or (isinstance(price, str) and "zdarma" in price.lower())):
            return True
    return False


def load(day_dir):
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(day_dir.glob("*.json"))}


def main():
    days = sorted(d for d in SNAP.iterdir() if d.is_dir())
    latest = load(days[-1])

    subjects = []
    for slug, d in latest.items():
        p = d.get("cremation_prices") or {}
        w = d.get("website_features") or {}
        t = d.get("transport") or {}
        r = d.get("reviews") or {}
        row = {
            "slug": slug,
            "name": d.get("name"),
            "operator": d.get("operator"),
            "kraj": d.get("kraj"),
            "type": d.get("type"),
            "type_label": TYPE_LABEL.get(d.get("type"), "nezjištěno"),
            "is_own": slug in OWN,
            "in_region": slug in REGION,
            **{COLS[c]: p.get(c) for c in CATS},
            "prices_include_vat": d.get("prices_include_vat"),
            "price_list_valid_from": d.get("price_list_valid_from"),
            "google_rating": r.get("google_rating"),
            "google_count": r.get("google_count"),
            "video_free": video_free(d),
            "online_order": bool(w.get("online_order")),
            "price_calculator": bool(w.get("price_calculator")),
            "nonstop_transport": bool(t.get("nonstop")),
            "url": (d.get("sources") or [None])[0],
            "checked_at": d.get("checked_at"),
        }
        subjects.append(row)

    history = []
    for day in days:
        for slug, d in load(day).items():
            p = d.get("cremation_prices") or {}
            for c in CATS:
                if p.get(c) is not None:
                    history.append({"date": day.name, "slug": slug, "is_own": slug in OWN,
                                    "in_region": slug in REGION, "category": c, "price": p.get(c)})

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "subjects.json").write_text(json.dumps(subjects, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"subjects: {len(subjects)} řádků, history: {len(history)} řádků, snapshoty: {[d.name for d in days]}")


if __name__ == "__main__":
    main()
