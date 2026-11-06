---
name: konkurence-check
description: Týdenní kontrola konkurence pro Memory Pet Krematorium. Stáhne aktuální stav webů konkurentů (ceny, služby, produkty, bonusy), porovná s minulým týdnem, zapíše report, commitne a pushne a při změnách pošle e-mail. Použij, když uživatel řekne "zkontroluj konkurenci", "/konkurence-check", nebo když to spustí týdenní rutina.
---

# Týdenní kontrola konkurence

Pracuj v kořeni repa. Nejdřív si přečti `CLAUDE.md` (pravidla), `competitors.yaml`, `data/schema.json` a `recommendations.md`.

`DNES` = dnešní datum ve formátu YYYY-MM-DD. `PREV` = nejnovější existující adresář v `data/snapshots/`.

## 1. Sběr snapshotů
Pro každý subjekt v `baseline` i `competitors` vytvoř `data/snapshots/DNES/<slug>.json` podle schématu.
- Paralelizuj: spusť subagenty (general-purpose), každý dostane 3–4 slugy a stejná pravidla jako v CLAUDE.md.
- Čti hlavně URL z `pages:`. Když `pages` chybí nebo vrací 404, najdi ceník ze hlavní stránky a `pages` v YAML oprav.
- **Úspora:** pro každou URL z `pages:` spočítej hash viditelného textu stránky: `curl -sL <url> | sed 's/<[^>]*>//g' | tr -s '[:space:]' | sha256sum` (WebFetch vrací jen shrnutí, hashuj přes curl). Hashe zapiš do `page_hashes`. Když se všechny shodují s `PREV/<slug>.json`, zkopíruj předchozí snapshot a změň jen `checked_at` a `page_hashes`, bez dalšího parsování.
- Když je web nedostupný, snapshot nevytvářej a poznamenej to do reportu (diff to ohlásí jako ⚠️).

## 2. Diff
Spusť `python scripts/diff_snapshots.py`. Exit 0 znamená beze změn, exit 1 znamená, že jsou změny.
Výstup skriptu je surový. Interpretuj ho: oddel skutečné změny (cena, nová služba, akce, nový produkt, změna hodnocení) od šumu (jinak formulovaný text) a šum vynech.

## 3. Měsíční discovery (jen první běh v měsíci)
Projdi `discovery_sources` v YAML a hledej nové subjekty, které ještě nejsou v `competitors`. Nové přidej do YAML s `priority` a uveď je v reportu.

## 4. Report `reports/weekly/DNES.md`
Struktura:
1. **TL;DR**: 3–5 odrážek, co je nového a co to znamená pro Memory Pet.
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

## 6. Notifikace (jen když jsou změny)
- Je-li dostupný Gmail connector: pošli e-mail na dara.novis@gmail.com, předmět `Konkurence DNES: <počet> změn`, tělo = TL;DR + odkaz na report na GitHubu (https://github.com/daranovis/konkurence/blob/main/reports/weekly/DNES.md).
- Jinak vytvoř GitHub issue se stejným obsahem a GitHub pošle notifikaci e-mailem.
- Když nejsou změny, nic neposílej.
