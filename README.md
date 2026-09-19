# SPC-ref – offline referenční nástroj k SPC (SÚKL)

Stav: **plný běh hotový (data SÚKL 09/2026), aplikace v0.1 postavená a otestovaná
na kompletní datové sadě.** Zbývá nasadit na GitHub Pages a vyzkoušet na iPhonu.

Výsledek plného běhu (19. 9. 2026):

| | |
|---|---|
| dokumentů v datové sadě | 4 048 (1 951 SÚKL + 2 097 SPC bloků z 1 541 EMA PDF) |
| kompletních (všech 7 sekcí) | 3 991 |
| částečných | 55 |
| bez jediné sekce | 2 (AURUM METALLICUM, ITUXREDI) |
| skenů / dokumentů bez textu | 0 |
| skupin ATC | 1 937 |
| dokumentů s dávkou na kg nebo m² | 1 126 |
| velikost pro aplikaci | 20 MB gzip (53 shardů + index) |

Seznam všech dokumentů s chybějící sekcí je v `etl/out/report.md` (sekce
„Dokumenty s chybějícími sekcemi"). Nejčastěji chybí bod 2 (19×) a 4.1 (16×) –
jde o SPC s nestandardním nadpisem; text v aplikaci u nich prostě není a je to
tam napsané.

Zásada projektu: aplikace nic negeneruje. Zobrazuje jen text SPC ze SÚKL,
výpočty dělá deterministický kód, u každého údaje je vidět přípravek a sekce.
Žádné LLM, žádné "AI shrnutí".

## Struktura

```
etl/
  sukl_etl.py        ETL: download, download-ema, run, export
  requirements.txt   pymupdf, certifi
  tests/             syntetická data + testy parseru (běží bez stahování)
docs/                aplikace (GitHub Pages servíruje složku /docs)
  index.html app.js style.css sw.js manifest.webmanifest icon*.png
  data/              vygenerovaná datová sada (export) – manifest.json, index.json.gz, docs-NNN.json.gz
README.md
```

## Co ETL dělá

1. `download` – z katalogu opendata.sukl.cz najde aktuální
   `DLPyyyymmdd.zip` (~10 MB, CSV win‑1250, `;`) a `SPCyyyymmdd.zip`
   (**~2,5 GB**, PDF/DOC) a stáhne je do `etl/data_raw/` (umí navázat přerušené stahování).
2. `run` – načte DLP, spáruje `dlp_lecivepripravky` ↔ `dlp_nazvydokumentu.SPC`,
   z každého SPC (čteno přímo ze zipu, bez rozbalování) vytáhne sekce
   2, 4.1–4.6, seskupí podle ATC kódu (primární jednotka; uvnitř skupiny
   zůstávají jednotlivé SPC dokumenty rozlišené), a zapíše:
   - `out/dataset_sample.json` (nebo `dataset.json`) – data pro aplikaci,
   - `out/stats.json` – čísla,
   - `out/report.md` – čitelný report včetně náhledu každé vytažené sekce.

Struktura tabulek a sloupců je ověřená proti aktuálnímu
`DLP_datove_rozhrani20260701.csv` (stav k 27. 8. 2026).

Výchozí filtr: `REG == R` (registrované) a bez PZLÚ (potraviny). Všechno, co
filtr vyřadí, je v reportu spočítané, nic se nezahazuje potichu.

## Zdroje dat a co o nich víme (změřeno na DLP 27. 8. 2026)

| | počet |
|---|---|
| kódů SÚKL v DLP | 69 759 (REG=R: 61 129) |
| lokálních SPC souborů (REG=R) | 7 372 (7 369 PDF, 3 DOC) |
| centralizovaně registrované (SPC jen na EMA/EC) | 13 327 kódů → **1 530 unikátních PDF**, přímé odkazy |
| skupin ATC celkem / jen přes EMA | 1 937 / ~40 % skupin má SPC jen na EMA |
| kódy bez SPC | 781 (769 homeopatika) |
| dodáváno v posl. 6 měsících | 8 825 kódů = 4 803 lokálních SPC + 843 EMA PDF |
| kombinací ATC × léková forma (lokální) | 1 951 |

Průměr textu sekcí 2 + 4.1–4.6 na jeden SPC dokument: **~14 000 znaků**
(rozpětí 4 000 – 35 000, měřeno na 7 reálných SPC).

### Rozsah (`--scope`) – odhad velikosti datasetu

| scope | lokální SPC | + EMA | odhad JSON | odhad gzip |
|---|---|---|---|---|
| `all` | 7 372 | 1 530 | ~160 MB | ~45 MB |
| `supplied` (DODAVKY=1) | 4 803 | 1 530 | ~120 MB | ~34 MB |
| `representative` (1 SPC na ATC×forma, přednost dodávaným a nejnovějším) | 1 951 | 1 530 | ~75 MB | ~20 MB |

EMA dokumenty se berou vždy všechny (jsou už unikátní na přípravek). Odhad EMA
části je nejistý – EMA SPC bývají delší; upřesní se po prvním plném běhu.
Obchodní názvy všech přípravků zůstávají ve vyhledávacích synonymech i ve
scope `representative`; aplikace u textu vždy ukáže, ze kterého SPC je a kolik
dalších SPC téhož ATC nebylo zahrnuto.

## Spuštění (fáze 1)

```bash
cd etl
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) stáhnout data (SPC zip má 2,5 GB – jednou, pak se používá lokálně)
python sukl_etl.py download
# 1b) stáhnout EMA/EC SPC (1 530 PDF, odhadem 1–3 GB; umí navázat, stažené přeskakuje)
python sukl_etl.py download-ema

# 2) náhodný vzorek 50 SPC dokumentů (+ 10 EMA)
python sukl_etl.py run --sample 50

# 3) celý dataset (výchozí scope = representative; --scope all / supplied pro jiný rozsah)
python sukl_etl.py run
# 4) export pro aplikaci -> docs/data/
python sukl_etl.py export

# volitelně cílené testy parseru:
python sukl_etl.py run --name ibuprofen          # všechny přípravky s "ibuprofen" v názvu
python sukl_etl.py run --codes 0094156,0210171   # konkrétní SÚKL kódy
python sukl_etl.py run --atc-prefix J01,N02 --sample 30
python sukl_etl.py run --dlp-only                # jen čísla z DLP, bez SPC zipu
```

Pak pošli `out/stats.json` a `out/report.md` (a případně 2–3 dokumenty,
u kterých vytažené sekce vypadají špatně).

Převod `.doc`: na macOS se použije vestavěný `textutil`, jinak `antiword`
nebo LibreOffice (`soffice --headless`). PDF čte PyMuPDF. Skeny (PDF bez
textové vrstvy) se detekují a označí jako `sken_nebo_bez_textu`; OCR se nedělá.

## Testy bez stahování

```bash
cd etl
python tests/make_fixtures.py     # vyrobí syntetické DLP/SPC zipy (cp1250, pdf/doc/docx, sken, EMA odkaz)
python sukl_etl.py --raw-dir tests/raw run --out-dir tests/out
python tests/test_parser.py       # varianty nadpisů, cp1250, regex dávky/kg
```

## Co ETL dělá s EMA dokumenty

`dlp_nazvydokumentu.SPC` u centralizovaně registrovaných přípravků obsahuje
přímý odkaz na CS "product information" PDF (EMA, u 34 přípravků EC community
register). Ten obsahuje PŘÍLOHU I (jeden nebo více SPC), PŘÍLOHU II a PŘÍLOHU
III (obaly + PIL). ETL uřízne vše od PŘÍLOHY II a každý blok začínající
`1. NÁZEV PŘÍPRAVKU` parsuje jako samostatné SPC (`url#1`, `url#2`, …). Balení
se k dílčímu SPC přiřadí podle síly v názvu, jinak ke všem.

## Co parser umí a co ne (ověřeno na reálných SPC)

- Nadpisy sekcí: `4.1 Terapeutické indikace`, `4.1. …`, VELKÁ PÍSMENA, číslo a
  název na dvou řádcích, bez diakritiky; odkazy "viz bod 4.4" uvnitř textu se
  za nadpis neberou (monotónní pořadí sekcí).
- Dávka na hmotnost/povrch: `5-10 mg ibuprofenu/kg tělesné hmotnosti`,
  `100 IU/kg (1 mg/kg)`, `2 mg/m²`, `20 ml přípravku X 5%/kg`, `40 ml … na kg`,
  kombinace `15 mg/3,75 mg/kg`, `20 mg/5 mg až 60 mg/15 mg na kg`. Ke každému
  výrazu se ukládá věta, ze které pochází; heuristicky i text intervalu
  (`dvakrát denně`, `každých 12 hodin`) – ten je jen informativní, aplikace s ním
  nepočítá.
- Neumí: tabulky dávkování (řádky tabulky se zachytí jako text věty, ne jako
  struktura), dávky vyjádřené jen v ml suspenze bez /kg, skeny (OCR se nedělá).
- Stav registrace: bere se `REG == R`; SÚKL u stavů B/C doporučuje hledat SPC
  u odpovídajícího přípravku se stavem R.
- `dlp_soli` se pro seskupování NEpoužívá – obsahuje i příbuzné látky
  (dexibuprofen → ibuprofen, estery, deriváty). Seskupení dělá ATC kód.
- Datum platnosti dat se bere z `dlp_platnost.csv` a zapisuje do `meta`.

## Měsíční aktualizace

```bash
python sukl_etl.py download        # stáhne jen nové zipy (starší nechá)
python sukl_etl.py run             # celý dataset
```
Postup nasazení nového datasetu do aplikace bude v README fáze 2.

## Aplikace (docs/)

Vanilla HTML/CSS/JS, bez buildu, bez knihoven, bez sítě po prvním načtení.

- **Data**: `docs/data/` = výstup `export` (gzip shardy). Při prvním spuštění se
  stáhnou do IndexedDB s ukazatelem postupu; přerušené načítání pokračuje tam,
  kde skončilo. Vyhledávací index (skupiny ATC + synonyma) je v paměti.
- **Hledání**: látka, obchodní název, synonymum, ATC; bez diakritiky, prefix,
  podřetězec, překlepy (editační vzdálenost 1, u delších slov 2). U výsledku je
  vidět, přes který název byl nalezen.
- **Detail**: skupina ATC → SPC v datové sadě (více jich jen když se liší
  léková forma) → sekce 2, 4.1–4.6 jako původní text (jen přeformátované
  zalomení řádků; tabulky z PDF zůstávají jako text). Nad každým blokem je
  zdroj: SPC soubor, sp. zn., datum rozhodnutí / odkaz na EMA PDF.
- **Výpočet dávky**: jen výrazy `X mg/kg`, `X IU/kg`, `X mg/m²`, kombinace
  `X mg/Y mg/kg` nalezené v bodě 4.2; hodnota × zadaná hmotnost (nebo × povrch
  těla, který zadáš sám – aplikace ho nepočítá). U každého výsledku je věta ze
  SPC. Intervaly, maxima a denní dávky aplikace nepočítá – čteš je ve větě.
  Bez výrazu v 4.2 se kalkulačka nenabízí.
- **Ledviny · játra · děti · senioři**: jen odstavce bodu 4.2, kde se tato slova
  vyskytují; jinak věta „SPC v bodě 4.2 o tomto nic neuvádí“. Žádný přepočet.
- **Křížový odkaz v textu SPC**: seznam léků → bod 4.5 každého z nich (volitelně
  i 4.3 a 4.4) se zvýrazněním míst, kde se objevuje název látky, přípravku
  nebo ATC skupiny jiného léku ze seznamu (porovnává se kmen slova bez
  diakritiky, aby prošlo skloňování). Nic víc – žádná závažnost, žádné barvy.
- **Připnuté a historie** na úvodní obrazovce, export/import JSON v „Data“.
- **Datum platnosti dat** v záhlaví; > 3 měsíce po konci platnosti = varování.
  Nová verze dat v repozitáři se nabídne k aktualizaci.

## Nasazení na GitHub Pages

1. Nový repozitář (klidně soukromý – Pages fungují i pro soukromý repozitář
   s GitHub Pro; jinak veřejný), nahrát celý obsah `spc-ref/`.
2. Settings → Pages → Build and deployment: *Deploy from a branch*, branch
   `main`, folder **/docs** → Save. Za minutu běží na
   `https://<user>.github.io/<repo>/`.
3. Na iPhonu otevřít v Safari, Sdílet → **Přidat na plochu**. První spuštění
   stáhne data (ukazatel postupu), pak funguje offline.
4. Po změně souborů aplikace (ne dat) zvyš `VERSION` v `docs/sw.js`, jinak
   telefon drží starou verzi z cache. V aplikaci je i tlačítko „Aktualizovat
   aplikaci (vymazat cache)“.

## Měsíční aktualizace dat

```bash
cd etl && source .venv/bin/activate
python sukl_etl.py download
python sukl_etl.py download-ema
python sukl_etl.py run
python sukl_etl.py export
cd .. && git add docs/data && git commit -m "data $(date +%Y-%m)" && git push
```
Aplikace při dalším spuštění s připojením nabídne nová data. Historie repozitáře
roste o velikost dat každý měsíc; když to začne vadit, stačí jednou za čas
historii zploštit (`git checkout --orphan`) – aplikace to neřeší.
