#!/usr/bin/env python3
"""Vyrobí syntetická testovací data se STEJNOU strukturou jako SÚKL zipy
(cp1250 + ';' CSV, SPCxxxx.pdf/.doc/.docx), aby šel pipeline otestovat bez
stahování 2,5 GB. Texty jsou vymyšlené – slouží jen k ověření parseru."""
from __future__ import annotations
import io, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
import pymupdf

HERE = Path(__file__).parent
RAW = HERE / "raw"
RAW.mkdir(exist_ok=True)


def csv_bytes(rows: list[list[str]]) -> bytes:
    return ("\r\n".join(";".join(r) for r in rows) + "\r\n").encode("cp1250")


def spc_text(name: str, sila: str, latka: str, variant: int) -> str:
    """Různé varianty formátování nadpisů, jak se v reálných SPC vyskytují."""
    h = {
        0: ("4.1 Terapeutické indikace", "4.2 Dávkování a způsob podání", "4.3 Kontraindikace",
            "4.4 Zvláštní upozornění a opatření pro použití",
            "4.5 Interakce s jinými léčivými přípravky a jiné formy interakce",
            "4.6 Fertilita, těhotenství a kojení", "4.7 Účinky na schopnost řídit a obsluhovat stroje"),
        1: ("4.1. Terapeutické indikace", "4.2. Dávkování a způsob podání", "4.3. Kontraindikace",
            "4.4. Zvláštní upozornění", "4.5. Interakce s jinými léčivými přípravky",
            "4.6. Těhotenství a kojení", "4.7. Účinky na schopnost řídit a obsluhovat stroje"),
        2: ("4.1 TERAPEUTICKÉ INDIKACE", "4.2 DÁVKOVÁNÍ A ZPŮSOB PODÁNÍ", "4.3 KONTRAINDIKACE",
            "4.4 ZVLÁŠTNÍ UPOZORNĚNÍ A OPATŘENÍ PRO POUŽITÍ", "4.5 INTERAKCE S JINÝMI LÉČIVÝMI PŘÍPRAVKY",
            "4.6 FERTILITA, TĚHOTENSTVÍ A KOJENÍ", "4.7 ÚČINKY NA SCHOPNOST ŘÍDIT A OBSLUHOVAT STROJE"),
    }[variant]
    return f"""sp. zn. sukls123456/2024

SOUHRN ÚDAJŮ O PŘÍPRAVKU

1. NÁZEV PŘÍPRAVKU

{name} {sila}

2. KVALITATIVNÍ A KVANTITATIVNÍ SLOŽENÍ

Jedna tableta obsahuje {latka} {sila}.
Úplný seznam pomocných látek viz bod 6.1.

3. LÉKOVÁ FORMA

Potahovaná tableta.

4. KLINICKÉ ÚDAJE

{h[0]}

Symptomatická léčba testovací bolesti u dospělých a dětí od 6 let (viz bod 4.2 a 4.4).

{h[1]}

Dávkování
Dospělí: 1 tableta 3x denně, maximálně 6 tablet denně.

Pediatrická populace
Děti od 6 let: 10–15 mg/kg tělesné hmotnosti každých 6–8 hodin, nejvýše 40 mg/kg/den.
Onkologické schéma: 2 mg/m² jednou týdně.

Porucha funkce ledvin
U pacientů s CrCl < 30 ml/min snižte dávku na polovinu (viz bod 4.4).

Způsob podání
Perorální podání, zapít vodou.

{h[2]}

Hypersenzitivita na léčivou látku. Aktivní vředová choroba.

{h[3]}

Opatrnosti je třeba u pacientů se srdečním selháním. Viz bod 4.5.

{h[4]}

Současné podání s warfarinem zvyšuje riziko krvácení. Inhibitory CYP3A4 zvyšují expozici.
Ibuprofen může snižovat účinek kyseliny acetylsalicylové.

{h[5]}

Nedoporučuje se ve třetím trimestru.

{h[6]}

Žádný vliv.

4.8 Nežádoucí účinky

Nauzea.

4.9 Předávkování

Symptomatická léčba.

5. FARMAKOLOGICKÉ VLASTNOSTI

5.1 Farmakodynamické vlastnosti

Farmakoterapeutická skupina: testovací.
"""


def _unicode_font() -> "pymupdf.Font":
    """Base14 Helvetica neumí č/ř/ž – vezmeme TTF ze systému (DejaVu/Liberation/Arial)."""
    import glob
    cands = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
             "/Library/Fonts/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
             "C:/Windows/Fonts/arial.ttf"]
    cands += glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True)
    for c in cands:
        if Path(c).exists():
            return pymupdf.Font(fontfile=c)
    print("VAROVÁNÍ: nenašel jsem TTF font s češtinou, PDF fixtura bude bez diakritiky")
    return pymupdf.Font("helv")


def make_pdf_unicode(text: str) -> bytes:
    """Helvetica v PyMuPDF neumí všechny české znaky – použijeme vestavěný font s CJK/latin fallbackem."""
    doc = pymupdf.open()
    lines = text.split("\n")
    n = 0
    total = len(lines) // 45 + 1
    while lines:
        chunk, lines = lines[:45], lines[45:]
        n += 1
        page = doc.new_page()
        tw = pymupdf.TextWriter(page.rect)
        font = _unicode_font()
        y = 60
        for l in chunk:
            tw.append((50, y), l, font=font, fontsize=9)
            y += 12
        tw.append((280, 800), f"{n}/{total}", font=font, fontsize=9)
        tw.write_text(page)
    out = doc.tobytes()
    doc.close()
    return out


def make_docx(text: str) -> bytes:
    def esc(x: str) -> str:
        return x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    paras = "".join(f"<w:p><w:r><w:t xml:space=\"preserve\">{esc(l)}</w:t></w:r></w:p>" for l in text.split("\n"))
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f'<w:body>{paras}</w:body></w:document>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
    return b.getvalue()


def make_doc_via_soffice(docx: bytes) -> bytes | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.docx"
        p.write_bytes(docx)
        subprocess.run([soffice, "--headless", "--convert-to", "doc", "--outdir", td, str(p)],
                       capture_output=True, timeout=300)
        out = Path(td) / "x.doc"
        return out.read_bytes() if out.exists() else None


def main() -> None:
    # ---- DLP ---------------------------------------------------------------
    lp = [["KOD_SUKL", "H", "NAZEV", "SILA", "FORMA", "BALENI", "CESTA", "DOPLNEK", "OBAL", "DRZ", "ZEMDRZ",
           "AKT_DRZ", "AKT_ZEM", "REG", "V_PLATDO", "NEOMEZ", "UVADENIDO", "IS_", "ATC_WHO", "RC", "SDOV",
           "SDOV_DOD", "SDOV_ZEM", "REG_PROC", "DDDAMNT_WHO", "DDDUN_WHO", "DDDP_WHO", "ZDROJ_WHO", "LL",
           "VYDEJ", "ZAV", "DOPING", "NARVLA", "DODAVKY", "EAN", "BRAILLOVO_PISMO", "EXP", "EXP_T",
           "NAZEV_REG", "MRP_CISLO", "PRAVNI_ZAKLAD_REGISTRACE", "OCHRANNY_PRVEK", "OMEZENI_PRESKRIPCE_SMP", "TYP_LP"]]
    def row(kod, nazev, sila, forma, baleni, reg, atc, rc, dod, typ="LP"):
        r = [""] * len(lp[0])
        r[0], r[2], r[3], r[4], r[5], r[6] = kod, nazev, sila, forma, baleni, "POR"
        r[13], r[18], r[19], r[33], r[38], r[43] = reg, atc, rc, dod, nazev, typ
        return r
    lp += [
        row("0000001", "IBALGIN TEST", "400MG", "TBL FLM", "24", "R", "M01AE01", "29/123/00-C", "A"),
        row("0000002", "IBALGIN TEST", "400MG", "TBL FLM", "48", "R", "M01AE01", "29/123/00-C", "A"),   # jiné balení, stejné SPC
        row("0000003", "BRUFEN TEST", "600MG", "GRA EFF", "20", "R", "M01AE01", "29/456/01-C", "A"),
        row("0000004", "NUROFEN TEST", "200MG", "TBL OBD", "12", "R", "M01AE01", "29/789/02-C", ""),
        row("0000005", "PARALEN TEST", "500MG", "TBL NOB", "24", "R", "N02BE01", "07/111/69-C", "A"),
        row("0000006", "STARY LEK TEST", "10MG", "TBL NOB", "30", "R", "C08CA01", "58/222/85-C", ""),    # sken
        row("0000007", "ELIQUIS TEST", "5MG", "TBL FLM", "60", "R", "B01AF02", "EU/1/11/691/008", "A"), # EMA odkaz
        row("0000008", "ZRUSENY TEST", "5MG", "TBL FLM", "60", "B", "M01AE01", "29/999/99-C", ""),      # jiný stav registrace
        row("0000009", "NUTRIDRINK TEST", "", "SOL", "4X200ML", "R", "V06DX", "", "A", "PZLU"),        # PZLÚ
        row("0000010", "AMLODIPIN TEST", "5MG", "TBL NOB", "30", "R", "C08CA01", "58/333/05-C", "A"),
    ]
    docs = [["KOD_SUKL", "PIL", "DAT_ROZ_PIL", "SPC", "DAT_ROZ_SPC", "OBAL_TEXT", "DAT_ROZ_OBAL", "NR", "DAT_NPM_NR"],
            ["0000001", "PI100001.pdf", "", "SPC100001.pdf", "2024-05-01", "", "", "", ""],
            ["0000002", "PI100001.pdf", "", "SPC100001.pdf", "2024-05-01", "", "", "", ""],
            ["0000003", "PI100003.doc", "", "SPC100003.doc", "2019-01-10", "", "", "", ""],
            ["0000004", "PI100004.docx", "", "SPC100004.docx", "2021-03-03", "", "", "", ""],
            ["0000005", "PI100005.pdf", "", "SPC100005.pdf", "2023-11-11", "", "", "", ""],
            ["0000006", "PI100006.pdf", "", "SPC100006.pdf", "2005-02-02", "", "", "", ""],
            ["0000007", "", "", "https://www.ema.europa.eu/en/medicines/human/EPAR/eliquis", "", "", "", "", ""],
            ["0000008", "", "", "SPC100008.pdf", "", "", "", "", ""],
            ["0000010", "", "", "SPC100010.pdf", "2022-07-07", "", "", "", ""]]
    latky = [["KOD_LATKY", "NAZEV_INN", "NAZEV_EN", "NAZEV", "ZAV"],
             ["100", "IBUPROFENUM", "IBUPROFEN", "IBUPROFEN", ""],
             ["101", "IBUPROFENUM LYSINICUM", "IBUPROFEN LYSINE", "IBUPROFEN-LYSIN", ""],
             ["200", "PARACETAMOLUM", "PARACETAMOL", "PARACETAMOL", ""],
             ["300", "AMLODIPINUM", "AMLODIPINE", "AMLODIPIN", ""],
             ["301", "AMLODIPINI BESILAS", "AMLODIPINE BESILATE", "AMLODIPIN-BESILÁT", ""],
             ["400", "APIXABANUM", "APIXABAN", "APIXABAN", ""]]
    soli = [["KOD_LATKY", "KOD_SOLI"], ["100", "101"], ["300", "301"]]
    priznak = [["S", "VYZNAM"], ["L", "léčivá látka"], ["P", "pomocná látka"], ["A", "léčivá látka – odpovídá"]]
    slozeni = [["KOD_SUKL", "KOD_LATKY", "SQ", "S", "AMNT_OD", "AMNT", "UN"]]
    for kod, lat, amnt in [("0000001", "100", "400"), ("0000002", "100", "400"), ("0000003", "100", "600"),
                           ("0000004", "101", "342"), ("0000004", "100", "200"), ("0000005", "200", "500"),
                           ("0000006", "301", "6.9"), ("0000006", "300", "5"), ("0000007", "400", "5"),
                           ("0000008", "100", "5"), ("0000010", "301", "6.9"), ("0000010", "300", "5")]:
        slozeni.append([kod, lat, "1", "L" if lat in ("100", "200", "300", "400") else "L", "", amnt, "MG"])
        slozeni.append([kod, "999", "9", "P", "", "PL", ""])
    synonyma = [["KOD_LATKY", "SQ", "ZDROJ", "NAZEV"], ["100", "1", "CZ", "IBUPROFEN"], ["100", "2", "EN", "IBUPROFEN"],
                ["300", "1", "CZ", "AMLODIPIN"], ["200", "1", "CZ", "PARACETAMOL"], ["200", "2", "EN", "ACETAMINOPHEN"]]
    atc = [["ATC", "NT", "NAZEV", "NAZEV_EN"], ["M01AE01", "N", "IBUPROFEN", "IBUPROFEN"],
           ["N02BE01", "N", "PARACETAMOL", "PARACETAMOL"], ["C08CA01", "N", "AMLODIPIN", "AMLODIPINE"],
           ["B01AF02", "N", "APIXABAN", "APIXABAN"], ["V06DX", "N", "JINÉ KOMBINACE VÝŽIVY", ""]]
    stavy = [["REG", "NAZEV"], ["R", "registrovaný léčivý přípravek"], ["B", "registrace zrušena – doprodej"]]
    typlp = [["TYP_LP", "NAZEV", "NAZEV_EN"], ["LP", "léčivý přípravek", "medicinal product"],
             ["PZLU", "potravina pro zvláštní lékařské účely", "food for special medical purposes"]]
    platnost = [["PLATNOST_OD", "PLATNOST_DO"], ["2026-09-01", "2026-09-30"]]
    formy = [["FORMA", "NAZEV", "NAZEV_EN", "NAZEV_LAT", "JE_KONOPI", "KOD_EDQM"],
             ["TBL FLM", "Potahovaná tableta", "", "", "", ""], ["TBL NOB", "Tableta", "", "", "", ""],
             ["GRA EFF", "Šumivé granule", "", "", "", ""], ["TBL OBD", "Obalená tableta", "", "", "", ""], ["SOL", "Roztok", "", "", "", ""]]
    cesty = [["CESTA", "NAZEV", "NAZEV_EN", "NAZEV_LAT", "KOD_EDQM"], ["POR", "Perorální podání", "", "", ""]]

    dlp_zip = RAW / "DLP20260901.zip"
    with zipfile.ZipFile(dlp_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for name, rows in {"dlp_lecivepripravky": lp, "dlp_nazvydokumentu": docs, "dlp_lecivelatky": latky,
                           "dlp_soli": soli, "dlp_slozenipriznak": priznak, "dlp_slozeni": slozeni,
                           "dlp_synonyma": synonyma, "dlp_atc": atc, "dlp_stavyreg": stavy, "dlp_typlp": typlp,
                           "dlp_platnost": platnost, "dlp_formy": formy, "dlp_cesty": cesty}.items():
            z.writestr(f"{name}.csv", csv_bytes(rows))

    # ---- SPC ---------------------------------------------------------------
    t1 = spc_text("Ibalgin Test", "400 mg", "ibuprofenum", 0)
    t3 = spc_text("Brufen Test", "600 mg", "ibuprofenum", 1)
    t4 = spc_text("Nurofen Test", "200 mg", "ibuprofenum", 2)
    t5 = spc_text("Paralen Test", "500 mg", "paracetamolum", 0)
    t10 = spc_text("Amlodipin Test", "5 mg", "amlodipinum", 1)
    docx3 = make_docx(t3)
    doc3 = make_doc_via_soffice(docx3)
    spc_zip = RAW / "SPC20260901.zip"
    with zipfile.ZipFile(spc_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("SPC100001.pdf", make_pdf_unicode(t1))
        if doc3:
            z.writestr("SPC100003.doc", doc3)
        else:
            print("VAROVÁNÍ: soffice nenalezen, SPC100003.doc se nevyrobil (test .doc se přeskočí)")
        z.writestr("SPC100004.docx", make_docx(t4))
        z.writestr("SPC100005.pdf", make_pdf_unicode(t5))
        # "sken": stránka jen s obrázkem, bez textu
        d = pymupdf.open(); p = d.new_page(); p.draw_rect(pymupdf.Rect(50, 50, 500, 700), color=(0, 0, 0)); 
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 200, 200), False); pix.clear_with(200)
        p.insert_image(pymupdf.Rect(50, 50, 500, 700), pixmap=pix)
        z.writestr("SPC100006.pdf", d.tobytes()); d.close()
        z.writestr("SPC100010.pdf", make_pdf_unicode(t10))
        # SPC100008.pdf záměrně chybí -> test "soubor v zipu nenalezen" (ale REG=B, takže se běžně nevybere)
    print("fixtures:", dlp_zip, spc_zip)


if __name__ == "__main__":
    main()
