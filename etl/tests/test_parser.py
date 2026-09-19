"""Rychlé testy parseru nadpisů (spusť: python -m pytest tests/ nebo python tests/test_parser.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sukl_etl import parse_spc, read_csv_bytes, DOSE_RE  # noqa: E402

BASE = """1. NÁZEV PŘÍPRAVKU
Testovin 10 mg
2. KVALITATIVNÍ A KVANTITATIVNÍ SLOŽENÍ
Jedna tableta obsahuje testovinum 10 mg.
3. LÉKOVÁ FORMA
Tableta
4. KLINICKÉ ÚDAJE
{h41}
Indikace A.
{h42}
Dávkování
Dospělí 10 mg denně.
{h43}
Přecitlivělost.
{h44}
Pozor (viz bod 4.5).
viz bod 4.5 Interakce – tohle je jen odkaz na začátku řádku, ne nadpis
{h45}
Warfarin.
{h46}
Kojení ne.
4.7 Účinky na schopnost řídit a obsluhovat stroje
Žádné.
5. FARMAKOLOGICKÉ VLASTNOSTI
5.1 Farmakodynamické vlastnosti
"""

VARIANTS = [
    dict(h41="4.1 Terapeutické indikace", h42="4.2 Dávkování a způsob podání", h43="4.3 Kontraindikace",
         h44="4.4 Zvláštní upozornění a opatření pro použití", h45="4.5 Interakce s jinými léčivými přípravky a jiné formy interakce",
         h46="4.6 Fertilita, těhotenství a kojení"),
    dict(h41="4.1. Terapeutické indikace", h42="4.2. Dávkování a způsob podání", h43="4.3. Kontraindikace",
         h44="4.4. Zvláštní upozornění", h45="4.5. Interakce s jinými léčivými přípravky", h46="4.6. Těhotenství a kojení"),
    dict(h41="4.1 TERAPEUTICKÉ INDIKACE", h42="4.2 DÁVKOVÁNÍ A ZPŮSOB PODÁNÍ", h43="4.3 KONTRAINDIKACE",
         h44="4.4 ZVLÁŠTNÍ UPOZORNĚNÍ A OPATŘENÍ PRO POUŽITÍ", h45="4.5 INTERAKCE S JINÝMI LÉČIVÝMI PŘÍPRAVKY",
         h46="4.6 FERTILITA, TĚHOTENSTVÍ A KOJENÍ"),
    # číslo a název na oddělených řádcích (typické pro .doc převody)
    dict(h41="4.1\nTerapeutické indikace", h42="4.2\nDávkování a způsob podání", h43="4.3\nKontraindikace",
         h44="4.4\nZvláštní upozornění a opatření pro použití", h45="4.5\nInterakce s jinými léčivými přípravky",
         h46="4.6\nFertilita, těhotenství a kojení"),
    # bez diakritiky (starší převody)
    dict(h41="4.1 Terapeuticke indikace", h42="4.2 Davkovani a zpusob podani", h43="4.3 Kontraindikace",
         h44="4.4 Zvlastni upozorneni", h45="4.5 Interakce", h46="4.6 Tehotenstvi a kojeni"),
]


def test_variants():
    for i, v in enumerate(VARIANTS):
        r = parse_spc(BASE.format(**v))
        assert r["chybi"] == [], f"varianta {i}: chybí {r['chybi']}, nalezeno {r['nalezene_nadpisy']}"
        s = r["sekce"]
        assert s["2"].startswith("Jedna tableta"), (i, s["2"])
        assert s["4.1"] == "Indikace A.", (i, s["4.1"])
        assert s["4.2"].startswith("Dávkování"), (i, s["4.2"])
        assert s["4.3"] == "Přecitlivělost.", (i, s["4.3"])
        assert "viz bod 4.5 Interakce" in s["4.4"], (i, s["4.4"])  # odkaz zůstal v 4.4, nebyl brán jako nadpis
        assert s["4.5"] == "Warfarin.", (i, s["4.5"])
        assert s["4.6"] == "Kojení ne.", (i, s["4.6"])


def test_missing_section_reported():
    v = dict(VARIANTS[0]); v["h46"] = "4.6 Něco úplně jiného"
    r = parse_spc(BASE.format(**v))
    assert r["chybi"] == ["4.6"], r["chybi"]
    assert r["sekce"]["4.5"].startswith("Warfarin."), r["sekce"]["4.5"]  # 4.5 sahá až k 4.7


def test_csv_cp1250():
    raw = "KOD_SUKL;NAZEV\r\n0000001;PŘÍPRAVEK ŽLUŤOUČKÝ\r\n".encode("cp1250")
    rows = read_csv_bytes(raw)
    assert rows[0]["NAZEV"] == "PŘÍPRAVEK ŽLUŤOUČKÝ"
    raw2 = "\ufeffKOD_SUKL,NAZEV\n0000001,ŽLUŤOUČKÝ\n".encode("utf-8")
    assert read_csv_bytes(raw2)[0]["NAZEV"] == "ŽLUŤOUČKÝ"


def test_dose_regex():
    txt = "Doporučená dávka je 10–15 mg/kg každých 6 hodin; max. 40 mg/kg/den. Onkologie 2 mg/m² týdně. 5 kg balení."
    hits = [m.group(0) for m in DOSE_RE.finditer(txt)]
    assert hits[0].startswith("10–15 mg/kg") and "40 mg/kg/den" in hits[1] and "2 mg/m²" in hits[2], hits
    assert len(hits) == 3, hits



def test_ema_split():
    from sukl_etl import parse_ema
    v = VARIANTS[0]
    spc = BASE.format(**v)
    doc = ("PŘÍLOHA I\nSOUHRN ÚDAJŮ O PŘÍPRAVKU\n▼Tento léčivý přípravek podléhá dalšímu sledování.\n"
           + spc.replace("Testovin 10 mg", "Testovin 10 mg potahované tablety\nTestovin 25 mg potahované tablety")
           + "\n" + spc.replace("Testovin 10 mg", "Testovin 5 mg perorální roztok")
           + "\nPŘÍLOHA II\nA. VÝROBCE\nPŘÍLOHA III\nPŘÍBALOVÁ INFORMACE\n1. NÁZEV PŘÍPRAVKU\nTestovin\n4.2 tohle je PIL a nesmí se parsovat\n")
    parts = parse_ema(doc)
    assert len(parts) == 2, [p.get("nazev_spc") for p in parts]
    assert parts[0]["nazev_spc"].startswith("Testovin 10 mg") and "25 mg" in parts[0]["nazev_spc"]
    assert parts[1]["nazev_spc"] == "Testovin 5 mg perorální roztok"
    assert all(p["chybi"] == [] for p in parts)
    assert parts[1]["sekce"]["4.2"].startswith("Dávkování")


def test_dose_combo_and_between():
    from sukl_etl import analyze_42
    t = ("Děti < 40 kg: 20 mg/5 mg až 60 mg/15 mg na kg denně ve třech dílčích dávkách.\n"
         "CrCl 10-30: 15 mg/3,75 mg/kg dvakrát denně.\n"
         "Jednotlivá dávka 5-10 mg ibuprofenu/kg tělesné hmotnosti. Balení 5 kg. Onkologie 2 mg/m² týdně.\n")
    d = analyze_42(t)["davky_na_hmotnost"]
    assert [x["typ"] for x in d] == ["kombinace", "kombinace", "jednoducha", "jednoducha"], [x["text"] for x in d]
    assert d[0]["slozky_od"] == [20.0, 5.0] and d[0]["slozky_do"] == [60.0, 15.0] and d[0]["interval"] == "denně"
    assert d[1]["slozky_od"] == [15.0, 3.75] and d[1]["interval"] == "dvakrát denně"
    assert d[2]["od"] == 5.0 and d[2]["do"] == 10.0 and d[2]["na"] == "kg"
    assert d[3]["na"] == "m2"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("OK", name)
