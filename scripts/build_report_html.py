"""Vygeneruje HTML report konkurence ze snapshotů (pro tisk do PDF).

Použití:
    python scripts/build_report_html.py [SNAPSHOT_DIR] [OUT_HTML] [--test]

--test přidá ukázkovou (simulovanou) sekci změn a označení TESTOVACÍ VÝSTUP.
PDF:  msedge --headless --no-pdf-header-footer --print-to-pdf=OUT.pdf file:///OUT.html
"""
import html
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATS = ["0-1", "1-5", "5-10", "10-20", "20-40", "40-60", "60+"]
BASELINE = {"memorypet", "memorypetpoint"}
MP_TRANSPORT = {"Liberec / Jablonec": "750", "Ústí / Teplice / Děčín": "750", "Praha": "1 450", "Hradec Králové / Trutnov": "1 950"}
COMP_TRANSPORT = {
    "Liberec / Jablonec": "KZ Liberec 750 paušál po kraji, příjezd 30–90 min",
    "Ústí / Teplice / Děčín": "KZ Ústí 750 po kraji; Kerberos 990",
    "Praha": "KZ Praha 990; Kerberos 990; Goodbye 990 (do 2 h)",
    "Hradec Králové / Trutnov": "Fatima km × 2 × 22 + 790 (min. 1 090)",
}

e = html.escape


def kc(v):
    return "–" if v is None else f"{int(v):,}".replace(",", " ")


def load(snap_dir: Path):
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(snap_dir.glob("*.json"))}


def price_table(data):
    comps = {s: d for s, d in data.items() if s not in BASELINE and any((d.get("cremation_prices") or {}).get(c) for c in CATS)}
    med = {}
    for c in CATS:
        vals = [d["cremation_prices"][c] for d in comps.values() if d["cremation_prices"].get(c)]
        med[c] = statistics.median(vals) if vals else None
    mp = data["memorypet"]["cremation_prices"]

    rows = ["<tr class='mp'><td>Memory Pet</td>" + "".join(f"<td>{kc(mp.get(c))}</td>" for c in CATS) + "</tr>"]
    rows.append("<tr class='med'><td>Medián konkurence</td>" + "".join(f"<td>{kc(med[c])}</td>" for c in CATS) + "</tr>")
    rows.append("<tr class='diff'><td>Memory Pet vs. medián</td>" + "".join(
        f"<td>{'–' if not (mp.get(c) and med[c]) else ('−' if mp[c] < med[c] else '+') + kc(abs(mp[c] - med[c]))}</td>" for c in CATS) + "</tr>")
    for s, d in sorted(comps.items(), key=lambda kv: kv[1]["cremation_prices"].get("10-20") or 1e9):
        p = d["cremation_prices"]
        cells = []
        for c in CATS:
            v = p.get(c)
            cls = ""
            if v and mp.get(c):
                cls = " class='lo'" if v < mp[c] else (" class='hi'" if v > mp[c] else "")
            cells.append(f"<td{cls}>{kc(v)}</td>")
        rows.append(f"<tr><td>{e(d.get('name', s))}</td>{''.join(cells)}</tr>")
    head = "<tr><th>Subjekt</th>" + "".join(f"<th>{c} kg</th>" for c in CATS) + "</tr>"
    return f"<table class='prices'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def recommendations(limit=10):
    lines = (ROOT / "recommendations.md").read_text(encoding="utf-8").splitlines()
    rows = []
    for ln in lines:
        cols = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cols) == 7 and cols[0].isdigit():
            rows.append(cols)
    out = "".join(f"<tr><td>{e(r[0])}</td><td>{e(r[1])}</td><td class='nw'>{e(r[2])}</td><td>{e(r[3])}</td><td>{e(r[4])}</td><td>{e(r[5])}</td></tr>" for r in rows[:limit])
    return ("<table><thead><tr><th>#</th><th>Doporučení</th><th>Kategorie</th><th>Náročnost</th><th>Dopad</th><th>Stav</th></tr></thead>"
            f"<tbody>{out}</tbody></table><p class='note'>Celkem {len(rows)} doporučení – zbytek v recommendations.md.</p>")


def build(snap_dir: Path, test: bool):
    data = load(snap_dir)
    date = snap_dir.name
    d_cz = ". ".join(str(int(x)) for x in reversed(date.split("-")[1:])) + ". " + date[:4]
    missing = [d.get("name", s) for s, d in data.items() if not any((d.get("cremation_prices") or {}).get(c) for c in CATS) and s not in BASELINE]

    test_banner = "<div class='test'>TESTOVACÍ VÝSTUP – ukázka formátu týdenního reportu</div>" if test else ""
    changes = ""
    if test:
        changes = """
<h2>1. Změny proti minulému týdnu</h2>
<p class='note'>Toto je první běh, není s čím porovnat. Níže je <b>simulovaná ukázka</b>, jak bude sekce vypadat, když konkurent něco změní.</p>
<table><thead><tr><th>Subjekt</th><th>Co se změnilo</th><th>Původně</th><th>Nově</th><th>Dopad pro Memory Pet</th></tr></thead><tbody>
<tr><td>Kremace zvířat Liberec</td><td>Cena 1–5 kg</td><td>3 990 Kč</td><td>3 490 Kč</td><td>Rozdíl oproti Memory Pet (3 300 Kč) se zmenšil na 190 Kč</td></tr>
<tr><td>Kremace zvířat Liberec</td><td>Nová akce</td><td>–</td><td>sleva 10 % (TEST)</td><td>Zvážit komunikaci vlastních slev na úvodní stránce</td></tr>
</tbody></table>"""
    n = 2 if test else 1

    return f"""<!doctype html><html lang="cs"><head><meta charset="utf-8"><title>Report konkurence {date}</title>
<style>
@page {{ size: A4; margin: 14mm 12mm 16mm; }}
body {{ font-family: Arial, sans-serif; font-size: 9.5pt; color: #1f2933; line-height: 1.4; }}
header {{ border-bottom: 3px solid #5b4b8a; padding-bottom: 6px; margin-bottom: 10px; }}
h1 {{ font-size: 18pt; margin: 0; color: #3d2f6b; }}
.sub {{ color: #616e7c; font-size: 9pt; }}
h2 {{ font-size: 12pt; color: #3d2f6b; margin: 16px 0 6px; border-bottom: 1px solid #d9d4e8; padding-bottom: 2px; page-break-after: avoid; }}
.test {{ background: #fff4e5; border: 1px solid #f0a14a; color: #8a4b00; padding: 5px 8px; font-weight: bold; margin-bottom: 10px; }}
ul {{ margin: 4px 0 4px 18px; padding: 0; }} li {{ margin-bottom: 3px; }}
table {{ border-collapse: collapse; width: 100%; margin: 4px 0; font-size: 8.5pt; page-break-inside: auto; }}
tr {{ page-break-inside: avoid; }}
th {{ background: #ece9f5; text-align: left; padding: 4px 5px; border-bottom: 1px solid #c7c0dd; }}
td {{ padding: 3px 5px; border-bottom: 1px solid #eceff3; }}
.prices td:not(:first-child), .prices th:not(:first-child) {{ text-align: right; white-space: nowrap; }}
tr.mp td {{ background: #e8e1fb; font-weight: bold; }}
tr.med td {{ background: #f4f6f8; font-style: italic; }}
tr.diff td {{ background: #eefaf1; color: #1e7b3a; font-weight: bold; }}
td.lo {{ color: #b42318; }} td.hi {{ color: #1e7b3a; }}
td.nw {{ white-space: nowrap; }}
.note {{ color: #616e7c; font-size: 8pt; margin: 3px 0; }}
.cols {{ display: flex; gap: 14px; }} .cols > div {{ flex: 1; }}
footer {{ margin-top: 14px; border-top: 1px solid #d9d4e8; padding-top: 5px; color: #616e7c; font-size: 7.5pt; }}
</style></head><body>
<header><h1>Memory Pet – týdenní report konkurence</h1>
<div class="sub">Stav k {d_cz} · {len(data) - len(BASELINE)} sledovaných subjektů v ČR · zdroj: veřejné weby konkurence</div></header>
{test_banner}
<h2>Shrnutí (TL;DR)</h2>
<ul>
<li><b>Cenou je Memory Pet pod trhem:</b> 1–5 kg za 3 300 Kč (medián 3 990 Kč), 10–20 kg za 5 300 Kč (nejčastěji 5 990 Kč). Web to ale nekomunikuje.</li>
<li><b>Hlavní soupeř v regionu je síť Krematorium zvířat Praha</b> s kancelářemi v Liberci a Ústí: svoz po kraji za 750 Kč, příjezd do 30–90 min, „Garance“ a video z kremace zdarma.</li>
<li><b>Online objednávku s okamžitou cenou</b> má 6 konkurentů, Memory Pet ne.</li>
<li><b>Svoz z Prahy (1 450 Kč) a vak navíc (450 Kč)</b> dělají Memory Pet pro pražské zákazníky dražším. Řešením je cena svozu nebo Memory Pet Point Praha 6.</li>
<li><b>Unikát Memory Pet Point</b> (samoobslužně 24/7) nemá v regionu nikdo, na webu je ale málo vidět.</li>
</ul>
{changes}
<h2>{n}. Ceny individuální kremace (Kč)</h2>
<p class="note">Červeně: levnější než Memory Pet · zeleně: dražší než Memory Pet. Kategorie konkurentů jsou přepočtené na váhové kategorie Memory Pet. Seřazeno podle ceny 10–20 kg.</p>
{price_table(data)}
<h2>{n + 1}. Svoz ve spádové oblasti</h2>
<table><thead><tr><th>Oblast</th><th>Memory Pet</th><th>Konkurence</th></tr></thead><tbody>
{''.join(f"<tr><td>{e(k)}</td><td>{v} Kč</td><td>{e(COMP_TRANSPORT[k])}</td></tr>" for k, v in MP_TRANSPORT.items())}
</tbody></table>
<h2>{n + 2}. Co mají konkurenti a Memory Pet ne</h2>
<ul>
<li><b>Video ze začátku kremace zdarma</b> (síť KZ Praha, Fatima, Vitem). Memory Pet: 990 Kč.</li>
<li><b>Pojmenovaná „Garance“</b> s vlastní stránkou: kód na kameni jde do pece i do urny, kamera.</li>
<li><b>Kalkulačka / online objednávka</b> (KZ Praha, Kerberos, Goodbye, Věčná loviště, Zlín).</li>
<li><b>Konkrétní slib doby příjezdu</b> (30–90 min, Goodbye do 2 h) a <b>bezplatná linka 800</b>.</li>
<li><b>Sleva pro zvířata z útulku</b> (PET HEAVEN, Fatima), <b>SMS při zahájení kremace</b> (Kerberos), <b>online sledování žehu</b> (KZ Praha, Brno, Zlín).</li>
</ul>
<h2>{n + 3}. Doporučení pro web (top 10)</h2>
{recommendations()}
<h2>{n + 4}. Problémy běhu</h2>
<ul>{''.join(f"<li>{e(m)}: web nešel přečíst, ceny chybí.</li>" for m in missing) or '<li>Žádné.</li>'}</ul>
<footer>Ceny převzaté z webů k {d_cz}, zdrojové URL jsou ve snapshotech data/snapshots/{date}/. Úplná data a historie: github.com/daranovis/konkurence · Vygenerováno automaticky.</footer>
</body></html>"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    test = "--test" in sys.argv
    snaps = sorted(d for d in (ROOT / "data" / "snapshots").iterdir() if d.is_dir())
    snap_dir = Path(args[0]) if args else snaps[-1]
    out = Path(args[1]) if len(args) > 1 else ROOT / "reports" / "pdf" / f"{snap_dir.name}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(snap_dir, test), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
