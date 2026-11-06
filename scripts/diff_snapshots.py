"""Porovná dva poslední snapshoty (data/snapshots/<datum>/) a vypíše změny v Markdownu.

Použití:
    python scripts/diff_snapshots.py                # dva nejnovější adresáře
    python scripts/diff_snapshots.py OLD_DIR NEW_DIR

Exit code: 0 = beze změn, 1 = jsou změny, 2 = chyba / chybí data.
Ignoruje pole, která se mění každý běh (checked_at, page_hashes, sources).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "data" / "snapshots"
IGNORE = {"checked_at", "page_hashes", "sources", "notes"}


def load_dir(d: Path) -> dict:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.json"))}


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not prefix and k in IGNORE:
                continue
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(obj, list):
        # seznamy porovnáváme jako množiny prvků (pořadí nehraje roli)
        out[prefix.rstrip(".")] = sorted(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in obj)
    else:
        out[prefix.rstrip(".")] = obj
    return out


def fmt(v):
    if isinstance(v, list):
        return ", ".join(json.loads(x) if x.startswith('"') else x for x in v) or "∅"
    return "∅" if v is None else str(v)


def diff_entity(old: dict, new: dict) -> list[str]:
    a, b = flatten(old), flatten(new)
    lines = []
    for key in sorted(set(a) | set(b)):
        va, vb = a.get(key), b.get(key)
        if va == vb:
            continue
        if isinstance(va, list) or isinstance(vb, list):
            sa, sb = set(va or []), set(vb or [])
            for x in sorted(sb - sa):
                lines.append(f"- **{key}** ➕ {fmt([x])}")
            for x in sorted(sa - sb):
                lines.append(f"- **{key}** ➖ {fmt([x])}")
        else:
            lines.append(f"- **{key}**: {fmt(va)} → {fmt(vb)}")
    return lines


def main():
    if len(sys.argv) == 3:
        old_dir, new_dir = Path(sys.argv[1]), Path(sys.argv[2])
    else:
        dirs = sorted(d for d in SNAP.iterdir() if d.is_dir()) if SNAP.exists() else []
        if len(dirs) < 2:
            print("Není s čím porovnat (méně než 2 snapshoty).")
            sys.exit(2)
        old_dir, new_dir = dirs[-2], dirs[-1]

    old, new = load_dir(old_dir), load_dir(new_dir)
    out, changed = [f"# Změny {old_dir.name} → {new_dir.name}", ""], False

    for slug in sorted(set(new) - set(old)):
        out.append(f"## 🆕 {new[slug].get('name', slug)} (`{slug}`) – nový subjekt"); changed = True
    for slug in sorted(set(old) - set(new)):
        out.append(f"## ⚠️ `{slug}` – v novém snapshotu chybí (web nedostupný / vyřazen?)"); changed = True
    for slug in sorted(set(old) & set(new)):
        lines = diff_entity(old[slug], new[slug])
        if lines:
            changed = True
            out += ["", f"## {new[slug].get('name', slug)} (`{slug}`)", *lines]

    if not changed:
        out.append("Beze změn.")
    print("\n".join(out))
    sys.exit(1 if changed else 0)


if __name__ == "__main__":
    main()
