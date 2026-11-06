---
name: konkurence-check
description: Týdenní kontrola konkurence pro Memory Pet Krematorium. Stáhne aktuální stav webů konkurentů (ceny, služby, produkty, bonusy), porovná s minulým týdnem, zapíše report, commitne a pushne a při změnách pošle e-mail. Použij, když uživatel řekne "zkontroluj konkurenci", "/konkurence-check", nebo když to spustí týdenní rutina.
---

# Týdenní kontrola konkurence

Pracuj v kořeni repa. Nejdřív si přečti `CLAUDE.md` (pravidla), `competitors.yaml`, `data/schema.json` a `recommendations.md`.

`DNES` = dnešní datum ve formátu YYYY-MM-DD. `PREV` = nejnovější existující adresář v `data/snapshots/`.
Předpoklad: `pip install -q pyyaml` (skripty čtou `competitors.yaml`).

## 0. Hledání nových konkurentů (každý týden)
Cíl: seznam konkurentů v `competitors.yaml` udržovat úplný. Noví se hned v tomto běhu analyzují.
1. Projdi `discovery.directories` (u firmy.cz všechny stránky výpisu), `discovery.network_pages` (nové pobočky známých sítí) a `discovery.search_queries` přes WebSearch. Dotaz s `{kraj}` spusť pro 4 kraje z `discovery.kraje_rotation[(číslo týdne v roce) mod 4]`.
2. Každý nalezený web porovnej podle domény s `baseline`, `competitors`, `candidates` i `excluded`. Známé přeskoč.
3. Nový subjekt otevři a ověř, že opravdu nabízí kremaci zvířat (vlastní pec / pobočka nebo sběrné místo / zprostředkovatel) a že web funguje.
   - **Ano:** přidej ho do `competitors` ve stejném formátu jako ostatní, s `added: DNES`, `found_via: <zdroj>`, `type`, `operator` a `priority` (high = Liberecký, Ústecký, Královéhradecký, Karlovarský kraj, Praha, Středočeský nebo velká síť; jinak medium/low).
   - **Ne** (hřbitov, lidská pohřební služba, jen e-shop s urnami, mrtvý web): přidej do `excluded` s `name`, `url`, `reason`, `date`.
4. Položky z `candidates` zkus znovu. Když web funguje, přesuň je do `competitors`.
5. Zkontroluj, že YAML je platný (`python -c "import yaml;yaml.safe_load(open('competitors.yaml',encoding='utf-8'))"`).

## 1. Sběr snapshotů
Pro každý subjekt v `baseline` i `competitors` (včetně nově přidaných v kroku 0) vytvoř `data/snapshots/DNES/<slug>.json` podle schématu. Noví nemají `PREV`, analyzuj je celé (ceník, služby, produkty, bonusy, slabiny, `notable`).
- Paralelizuj: spusť subagenty (general-purpose), každý dostane 3–4 slugy a stejná pravidla jako v CLAUDE.md.
- Čti hlavně URL z `pages:`. Když `pages` chybí nebo vrací 404, najdi ceník ze hlavní stránky a `pages` v YAML oprav.
- **Úspora:** pro každou URL z `pages:` spočítej hash viditelného textu stránky: `curl -sL <url> | sed 's/<[^>]*>//g' | tr -s '[:space:]' | sha256sum` (WebFetch vrací jen shrnutí, hashuj přes curl). Hashe zapiš do `page_hashes`. Když se všechny shodují s `PREV/<slug>.json`, zkopíruj předchozí snapshot a změň jen `checked_at` a `page_hashes`, bez dalšího parsování.
- Když je web nedostupný, snapshot nevytvářej a poznamenej to do reportu (diff to ohlásí jako ⚠️).

## 2. Diff
Spusť `python scripts/diff_snapshots.py`. Exit 0 znamená beze změn, exit 1 znamená, že jsou změny.
Výstup skriptu je surový. Interpretuj ho: oddel skutečné změny (cena, nová služba, akce, nový produkt, změna hodnocení) od šumu (jinak formulovaný text) a šum vynech.

## 2b. Data pro dashboard
Spusť `python scripts/build_dashboard_data.py`. Přegeneruje `data/dashboard/subjects.json` a `history.json` ze snapshotů a dashboard (https://claude.ai/artifact/2aYcW4mPAP6HyNVsdroR8f) je pak z nich možné aktualizovat. Pokud máš nástroje Artifact/ArtifactData, nahraj oba soubory do dashboardu jako nové assety a v datasetech `subjects` a `history` aktualizuj `source.url` a `updated`. Jinak to v reportu uveď jako krok, který udělá Claude na požádání.

## 3. Seznam konkurentů
Spusť `python scripts/build_competitor_list.py`. Přegeneruje čitelný `konkurenti.md`.

## 4. Report `reports/weekly/DNES.md`
Struktura:
1. **TL;DR**: 3–5 odrážek, co je nového a co to znamená pro Memory Pet.
1b. **Noví konkurenti**: pro každý nově přidaný subjekt krátká analýza (kde je, typ, ceny 1–5 a 10–20 kg vs. Memory Pet, svoz, zajímavé služby a bonusy, co z toho plyne). Uveď i počet vyřazených nálezů. Když nikdo nový nepřibyl, napiš „Žádní noví konkurenti (prohledáno: <zdroje>, kraje <rotace>)“.
2. **Změny cen**: tabulka subjekt / kategorie / staré → nové.
3. **Nové služby, produkty, akce a bonusy.**
4. **Recenze**: změny Google hodnocení a počtu recenzí.
5. **Stav Memory Pet**: změnilo se něco na našem webu? Platí ještě otevřená doporučení?
6. **Nová doporučení**: přidej je do `recommendations.md` se stavem `navrženo`. Nenavrhuj nic, co je tam jako `zamítnuto`.
7. **Problémy běhu**: nedostupné weby nebo texty mířené na AI, které weby obsahovaly.

Když nejsou změny, report má jen „Beze změn“ a krátký přehled stavu.

## 5. Commit a push
```
git add -A
git commit -m "Týdenní kontrola konkurence DNES"
git push origin main
```

## 6. Notifikace (jen když jsou změny nebo noví konkurenti)
- Je-li dostupný Gmail connector: pošli e-mail na dara.novis@gmail.com, předmět `Konkurence DNES: <počet> změn`, tělo = TL;DR + odkaz na report na GitHubu (https://github.com/daranovis/konkurence/blob/main/reports/weekly/DNES.md).
- Jinak vytvoř GitHub issue se stejným obsahem a GitHub pošle notifikaci e-mailem.
- Když nejsou změny, nic neposílej.
