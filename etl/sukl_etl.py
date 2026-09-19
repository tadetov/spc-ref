#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sukl_etl.py – jednorázový / opakovatelný ETL nad otevřenými daty SÚKL
(opendata.sukl.cz): Databáze léčivých přípravků (DLP) + texty SPC.

Výstup: kompaktní JSON datová sada (primární jednotka = účinná látka),
statistika běhu a report o tom, co se NEPODAŘILO vytáhnout.

Skript NIC negeneruje ani nedomýšlí – jen slicuje oficiální text SPC podle
nadpisů sekcí a deterministicky hledá výrazy typu "X mg/kg".

Použití (viz README):
    python sukl_etl.py download                  # stáhne aktuální DLP + SPC zip
    python sukl_etl.py run --sample 50           # ETL na náhodném vzorku 50 přípravků
    python sukl_etl.py run --name ibuprofen      # ETL na přípravcích, jejichž název obsahuje řetězec
    python sukl_etl.py run --codes 0094156,0210171
    python sukl_etl.py run                       # celý dataset

Závislosti: Python 3.10+, pymupdf (pip install pymupdf).
Pro .doc: macOS `textutil` (vestavěné) nebo `antiword` nebo LibreOffice `soffice`.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

try:
    import pymupdf  # type: ignore
except ImportError:  # pragma: no cover
    pymupdf = None

CATALOG_DLP = "https://opendata.sukl.cz/?q=katalog/databaze-lecivych-pripravku-dlp"
CATALOG_SPC = "https://opendata.sukl.cz/?q=katalog/spc-souhrn-udaju-o-lecivem-pripravku-summary-product-characteristics"

SCHEMA_VERSION = 1

# Sekce, které chceme (v pořadí, v jakém jdou v SPC). Klíč -> (regex čísla, regex názvu).
# Pořadí je důležité: konec sekce = začátek nejbližší další nalezené sekce.
SECTION_DEFS: list[tuple[str, str, str]] = [
    ("1",   r"1",        r"N[AÁ]ZEV\s+P[RŘ][IÍ]PRAVKU"),
    ("2",   r"2",        r"KVALITATIVN[IÍ]\b"),  # tolerantní: v praxi i překlepy typu KVANTITAVNÍ
    ("3",   r"3",        r"L[EÉ]KOV[AÁ]\s+FORMA"),
    ("4",   r"4",        r"KLINICK[EÉ]\s+[UÚ]DAJE"),
    ("4.1", r"4\.\s?1",  r"Terapeutick[eé]\s+indikace"),
    ("4.2", r"4\.\s?2",  r"D[aá]vkov[aá]n[ií](?:\s+a\s+zp[uů]sob\s+pod[aá]n[ií])?"),
    ("4.3", r"4\.\s?3",  r"Kontraindikace"),
    ("4.4", r"4\.\s?4",  r"Zvl[aá][sš]tn[ií]\s+upozorn[eě]n[ií]"),
    ("4.5", r"4\.\s?5",  r"Interakce"),
    ("4.6", r"4\.\s?6",  r"(?:Fertilita|T[eě]hotenstv[ií]|Plodnost)"),
    ("4.7", r"4\.\s?7",  r"[UÚ][cč]inky\s+na\s+schopnost"),
    ("4.8", r"4\.\s?8",  r"Ne[zž][aá]douc[ií]\s+[uú][cč]inky"),
    ("4.9", r"4\.\s?9",  r"P[rř]ed[aá]vkov[aá]n[ií]"),
    ("5",   r"5",        r"FARMAKOLOGICK[EÉ]\s+VLASTNOSTI"),
    ("5.1", r"5\.\s?1",  r"Farmakodynamick[eé]"),
    ("6",   r"6",        r"FARMACEUTICK[EÉ]\s+[UÚ]DAJE"),
]
WANTED_SECTIONS = ["2", "4.1", "4.2", "4.3", "4.4", "4.5", "4.6"]
SECTION_TITLES = {
    "2": "Kvalitativní a kvantitativní složení",
    "4.1": "Terapeutické indikace",
    "4.2": "Dávkování a způsob podání",
    "4.3": "Kontraindikace",
    "4.4": "Zvláštní upozornění a opatření pro použití",
    "4.5": "Interakce s jinými léčivými přípravky a jiné formy interakce",
    "4.6": "Fertilita, těhotenství a kojení",
}

# Podnadpisy uvnitř 4.2, jejichž PŘÍTOMNOST zaznamenáme (bez interpretace).
# Podnadpis = krátký řádek bez koncové tečky, obsahující klíčové slovo.
SUBHEAD_42 = {
    "pediatrie": r"pediatrick|d[eě]ti\b|d[eě]tsk|kojenc|dosp[ií]vaj",
    "ledviny": r"ledvin|ren[aá]ln",
    "jatra": r"jater|jatern|hepat",
    "seniori": r"star[sš][ií]|geriatr|senio[rř]",
}

# Deterministické hledání dávky vztažené k hmotnosti / povrchu těla.
# Pokrývá "5-10 mg ibuprofenu/kg tělesné hmotnosti/den", "100 IU/kg", "2 mg/m²",
# "20 ml přípravku Aminoven 5%/kg", "40 ml ... na kg" a kombinace "15 mg/3,75 mg/kg".
_NUM = r"\d+(?:[,.]\d+)?"
_UNIT = r"(?:mg|g|µg|μg|mcg|mikrogram(?:y|ů|u)?|IU|I\.?U\.?|m\.?j\.?|MIU|milion[uů]?\s+IU|j\.|ml|mmol|kapk[ay]|dávk[ay])"
_BETWEEN = r"(?:\s+(?:[^\s/\d][^\s/]*|\d+(?:[,.]\d+)?%)){0,3}?"  # název látky/přípravku mezi jednotkou a /kg
_PER = r"(?:/\s*|\s+na\s+)(?:kg|m\s?2|m²)"
_BW = r"(?:\s*(?:t[eě]lesn[eé]\s+hmotnosti|t[eě]l\.?\s?hm\.?|t\.\s?hm\.?|TH))?"
DOSE_RE = re.compile(
    rf"(?P<od>{_NUM})(?:\s*(?:–|-|—|až|do)\s*(?P<do>{_NUM}))?\s*(?P<jednotka>{_UNIT}){_BETWEEN}\s*(?P<per>{_PER}){_BW}"
    rf"(?:\s*(?P<perday>/\s*(?:den|d|24\s*h(?:od)?\.?|hod\.?|h)))?",
    re.IGNORECASE,
)
# Fixní kombinace: "15 mg/3,75 mg/kg", "20 mg/5 mg až 60 mg/15 mg na kg"
_PAIR = rf"(?:{_NUM})\s*(?:{_UNIT})\s*/\s*(?:{_NUM})\s*(?:{_UNIT})"
COMBO_RE = re.compile(
    rf"(?P<a>{_PAIR})(?:\s*(?:–|-|—|až)\s*(?P<b>{_PAIR}))?\s*(?P<per>{_PER}){_BW}"
    rf"(?:\s*(?P<perday>/\s*(?:den|d|24\s*h(?:od)?\.?)))?",
    re.IGNORECASE,
)
# Interval podání hledaný v následujících ~60 znacích za výrazem (jen záznam textu, žádná interpretace)
INTERVAL_RE = re.compile(
    r"(?:(?:jednou|dvakr[aá]t|t[rř]ikr[aá]t|[čc]ty[rř]ikr[aá]t|\d+\s?x)\s+denn[eě]"
    r"|denn[eě]|za\s+den|ka[žz]d[ýy]ch\s+\d+(?:\s*(?:–|-|až)\s*\d+)?\s*(?:hodin|h\b|hod\.?)"
    r"|ka[žz]d[ýy]\s+den|jednou\s+t[ýy]dn[eě]|t[ýy]dn[eě]|v\s+jedn[ée]\s+d[aá]vce|ve\s+\d+(?:\s*(?:–|-|až)\s*\d+)?\s+d[ií]l[čc][ií]ch\s+d[aá]vk[aá]ch"
    r"|rozd[eě]len[eě]\s+(?:ve|do)\s+\d+(?:\s*(?:–|-|až)\s*\d+)?\s+(?:d[aá]vek|d[ií]l[čc][ií]ch\s+d[aá]vk[aá]ch))",
    re.IGNORECASE,
)

PAGE_FOOTER_RES = [
    re.compile(r"^\s*\d{1,3}\s*/\s*\d{1,3}\s*$"),
    re.compile(r"^\s*Strana\s+\d+\s*(?:\(celkem\s+\d+\))?\s*$", re.IGNORECASE),
    re.compile(r"^\s*Str(?:ana|\.)\s*\d+\s*(?:z|/)\s*\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d{1,3}\s*$"),
]


# ----------------------------------------------------------------------------
# Pomocné funkce
# ----------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def strip_diacritics_keep_len(s: str) -> str:
    """Odstraní diakritiku, ale zachová DÉLKU řetězce (1 znak -> 1 znak),
    aby pozice z regexu seděly do původního textu."""
    out = []
    for ch in s:
        d = unicodedata.normalize("NFD", ch)
        base = d[0] if d else ch
        out.append(base if unicodedata.category(base) != "Mn" else ch)
    return "".join(out)


def slug(s: str) -> str:
    s = strip_diacritics_keep_len(s.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "x"


def read_csv_bytes(raw: bytes) -> list[dict]:
    """CSV ze SÚKL: většinou win-1250 + ';'. NKOD verze: UTF-8 BOM + ','.
    Zkusíme UTF-8 (strict), při chybě cp1250. Oddělovač z hlavičky."""
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1250")
    first = text.split("\n", 1)[0]
    delim = ";" if first.count(";") >= first.count(",") else ","
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delim))
    # ořez mezer v hlavičce i hodnotách
    return [{(k or "").strip().upper(): (v or "").strip() for k, v in r.items()} for r in rows]


def _ssl_context():
    """Python z python.org na macOS nemá systémové certifikáty -> CERTIFICATE_VERIFY_FAILED.
    Když je nainstalovaný balíček certifi (je v requirements.txt), použijeme jeho kořenové certifikáty."""
    try:
        import ssl
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa
        return None


_SSL = _ssl_context()


UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) "
      "Version/17.0 Safari/605.1.15 spc-ref-etl/1.0")


RATE = {"hits429": 0}  # počítadlo omezení rychlosti (429) pro adaptivní zpomalování


def http_get(url: str, timeout: int = 60, retries: int = 6) -> bytes:
    """GET s opakováním. 429 = server omezuje rychlost: čeká se podle Retry-After (jinak 30, 60, 120, 240 s…),
    ostatní chyby 5, 20, 60 s. 404/410 se nevrací (odkaz je mrtvý)."""
    last: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*;q=0.8",
                                                   "Accept-Language": "cs,en;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (404, 410):
                raise
            if e.code == 429:
                RATE["hits429"] += 1
                ra = e.headers.get("Retry-After") if e.headers else None
                wait = min(600, int(ra)) if ra and ra.isdigit() else min(600, 30 * (2 ** attempt))
            else:
                wait = (5, 20, 60, 120, 240, 300)[min(attempt, 5)]
        except Exception as e:  # noqa
            last = e
            wait = (5, 20, 60, 120, 240, 300)[min(attempt, 5)]
        if attempt < retries:
            log(f"    {url.rsplit('/', 1)[-1]}: {type(last).__name__} {getattr(last, 'code', '')} – čekám {wait}s")
            time.sleep(wait)
    raise last  # type: ignore[misc]


def download_file(url: str, dest: Path, resume: bool = True) -> Path:
    """Stažení s podporou navázání (Range) a ukazatelem postupu."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    have = tmp.stat().st_size if (resume and tmp.exists()) else 0
    headers = {"User-Agent": UA}
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120, context=_SSL) as r:
        status = getattr(r, "status", 200)
        total = r.headers.get("Content-Length")
        total = int(total) + (have if status == 206 else 0) if total else None
        mode = "ab" if (status == 206 and have) else "wb"
        if mode == "wb":
            have = 0
        with open(tmp, mode) as f:
            t0 = time.time()
            done = have
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if time.time() - t0 > 2:
                    t0 = time.time()
                    pct = f"{100*done/total:5.1f} %" if total else ""
                    log(f"  {dest.name}: {done/2**20:8.1f} MB {pct}")
    tmp.rename(dest)
    log(f"  hotovo: {dest} ({dest.stat().st_size/2**20:.1f} MB)")
    return dest


def find_zip_links(catalog_url: str, pattern: str) -> list[str]:
    html = http_get(catalog_url).decode("utf-8", "replace")
    links = re.findall(r'href="([^"]*?' + pattern + r')"', html)
    links = [l if l.startswith("http") else "https://opendata.sukl.cz/" + l.lstrip("/") for l in links]
    return sorted(set(links), key=lambda u: u.rsplit("/", 1)[-1])


# ----------------------------------------------------------------------------
# Extrakce textu z dokumentů (PDF / DOC / DOCX / RTF)
# ----------------------------------------------------------------------------

def _clean_page_lines(page_text: str) -> str:
    lines = page_text.split("\n")
    # odstranit záhlaví/zápatí se stránkováním jen na okrajích stránky
    def is_footer(l: str) -> bool:
        return any(rx.match(l) for rx in PAGE_FOOTER_RES)
    i, j = 0, len(lines)
    while i < j and (not lines[i].strip() or is_footer(lines[i])):
        i += 1
    while j > i and (not lines[j - 1].strip() or is_footer(lines[j - 1])):
        j -= 1
    return "\n".join(lines[i:j])


def extract_pdf(data: bytes) -> tuple[str, dict]:
    if pymupdf is None:
        raise RuntimeError("pymupdf není nainstalováno: pip install pymupdf")
    doc = pymupdf.open(stream=data, filetype="pdf")
    pages = []
    n_img_pages = 0
    for page in doc:
        t = page.get_text("text")
        if len(t.strip()) < 30 and page.get_images():
            n_img_pages += 1
        pages.append(_clean_page_lines(t))
    text = "\n\n".join(pages)
    info = {"stran": len(doc), "znaku": len(text), "stran_bez_textu_s_obrazkem": n_img_pages}
    doc.close()
    return text, info


def extract_docx(data: bytes) -> tuple[str, dict]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    # odstavce -> řádky, tabulky se zploští po buňkách
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&apos;", "'"))
    return text, {"znaku": len(text)}


def _which(*names: str) -> str | None:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def extract_doc_binary(data: bytes, suffix: str) -> tuple[str, dict]:
    """Starý binární .doc / .rtf: textutil (macOS) -> antiword -> soffice."""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / f"in{suffix}"
        src.write_bytes(data)
        # 1) macOS textutil
        if _which("textutil"):
            r = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(src)],
                               capture_output=True, timeout=120)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.decode("utf-8", "replace"), {"nastroj": "textutil"}
        # 2) antiword (jen .doc)
        if suffix == ".doc" and _which("antiword"):
            r = subprocess.run(["antiword", "-w", "0", str(src)], capture_output=True, timeout=120)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.decode("utf-8", "replace"), {"nastroj": "antiword"}
        # 3) LibreOffice
        soffice = _which("soffice", "libreoffice")
        if soffice:
            r = subprocess.run([soffice, "--headless", "--convert-to", "txt:Text (encoded):UTF8",
                                "--outdir", td, str(src)], capture_output=True, timeout=300)
            out = Path(td) / "in.txt"
            if out.exists():
                return out.read_text("utf-8", "replace"), {"nastroj": "soffice"}
        raise RuntimeError("žádný převodník .doc (textutil/antiword/soffice) nenalezen nebo selhal")


def extract_text(name: str, data: bytes) -> tuple[str, str, dict]:
    """Vrátí (text, format, info). format = pdf|docx|doc|rtf|jiny."""
    ext = Path(name).suffix.lower()
    head = data[:8]
    if head.startswith(b"%PDF") or ext == ".pdf":
        t, i = extract_pdf(data)
        return t, "pdf", i
    if head.startswith(b"PK") or ext == ".docx":
        t, i = extract_docx(data)
        return t, "docx", i
    if head.startswith(b"{\\rtf") or ext == ".rtf":
        t, i = extract_doc_binary(data, ".rtf")
        return t, "rtf", i
    if head.startswith(b"\xd0\xcf\x11\xe0") or ext == ".doc":
        t, i = extract_doc_binary(data, ".doc")
        return t, "doc", i
    raise RuntimeError(f"neznámý formát souboru: {name}")


# ----------------------------------------------------------------------------
# Parsování sekcí
# ----------------------------------------------------------------------------

def normalize_text(t: str) -> str:
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = t.replace("\u00a0", " ").replace("\u2011", "-").replace("\u00ad", "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _heading_regex(num_re: str, title_re: str) -> re.Pattern:
    # číslo na začátku řádku, volitelná tečka, mezera/tab/newline, název sekce
    return re.compile(rf"(?im)^[ \t]*{num_re}\.?[ \t]*(?:\n[ \t]*)?{title_re}\b")


_HEAD_RES = [(key, _heading_regex(n, t)) for key, n, t in SECTION_DEFS]


def find_headings(text: str) -> dict[str, tuple[int, int]]:
    """Najde nadpisy v pořadí SECTION_DEFS. Vrací klíč -> (začátek nadpisu,
    konec řádku s nadpisem). Každý další nadpis musí ležet za předchozím
    nalezeným (monotónnost) – tím se vyřadí odkazy typu 'viz bod 4.4'."""
    plain = strip_diacritics_keep_len(text)
    pos: dict[str, tuple[int, int]] = {}
    last = 0
    for key, rx in _HEAD_RES:
        m = rx.search(plain, last)
        if m:
            eol = plain.find("\n", m.end())
            eol = len(plain) if eol < 0 else eol
            pos[key] = (m.start(), eol)
            last = m.start() + 1
    return pos


def slice_sections(text: str, pos: dict[str, tuple[int, int]]) -> dict[str, str]:
    starts = sorted(p[0] for p in pos.values())
    out: dict[str, str] = {}
    for key in WANTED_SECTIONS:
        if key not in pos:
            continue
        start, head_end = pos[key]
        later = [p for p in starts if p > start]
        end = min(later) if later else len(text)
        out[key] = text[head_end:end].strip()
    return out


def _is_subheading(line: str) -> bool:
    l = line.strip()
    return 0 < len(l) <= 90 and not l.endswith((".", ";", ",")) and not l.startswith(("•", "-", "–"))


def _sentence_around(text: str, start: int, end: int, max_len: int = 500) -> str:
    """Věta (případně dvě) kolem nálezu – hranice = tečka/středník + mezera + velké písmeno, nebo prázdný řádek."""
    left = max([m.end() for m in re.finditer(r"(?:[.;:]\s+(?=[A-ZÁ-Ž•])|\n\s*\n)", text[:start])] + [0])
    m = re.search(r"(?:[.;]\s+(?=[A-ZÁ-Ž•])|\n\s*\n|$)", text[end:])
    right = end + (m.start() if m else 0)
    snippet = text[left:right].strip()
    if len(snippet) > max_len:
        a = max(0, start - left - max_len // 2)
        snippet = ("…" if a else "") + snippet[a:a + max_len] + "…"
    return snippet


def analyze_42(text42: str) -> dict:
    """Deterministická analýza sekce 4.2: přítomnost podnadpisů + výrazy dávky/kg, /m2.
    Nic se neinterpretuje – jen se zaznamená, kde v textu co je."""
    flags = {}
    plain_lines = [(strip_diacritics_keep_len(l), l) for l in text42.split("\n")]
    for name, rx in SUBHEAD_42.items():
        r = re.compile(strip_diacritics_keep_len(rx), re.IGNORECASE)
        flags[name] = any(_is_subheading(l) and r.search(pl) for pl, l in plain_lines)
    davky = []
    taken: list[tuple[int, int]] = []

    def _num(x: str | None):
        return float(x.replace(",", ".")) if x else None

    def _interval(end: int) -> str | None:
        # jen do konce věty (tečka/středník + velké písmeno, nebo prázdný řádek), max 70 znaků
        stop = re.search(r"[.;]\s+(?=[A-ZÁ-Ž•])|\n\s*\n", text42[end:end + 70])
        lim = end + (stop.start() if stop else 70)
        m = INTERVAL_RE.search(text42, end, min(len(text42), lim))
        return re.sub(r"\s+", " ", m.group(0)) if m else None

    for m in COMBO_RE.finditer(text42):
        taken.append((m.start(), m.end()))
        per = "m2" if "m" in re.sub(r"[/\sna]", "", m.group("per")).lower() else "kg"
        nums_a = [_num(x) for x in re.findall(_NUM, m.group("a"))]
        nums_b = [_num(x) for x in re.findall(_NUM, m.group("b"))] if m.group("b") else None
        units = re.findall(_UNIT, m.group("a"), re.IGNORECASE)
        davky.append({
            "text": re.sub(r"\s+", " ", m.group(0)).strip(), "typ": "kombinace",
            "slozky_od": nums_a, "slozky_do": nums_b, "jednotky": units, "na": per,
            "za_den": bool(m.group("perday")), "interval": _interval(m.end()),
            "pozice": m.start(), "veta": re.sub(r"\s+", " ", _sentence_around(text42, m.start(), m.end())),
        })
    for m in DOSE_RE.finditer(text42):
        if any(a <= m.start() < b for a, b in taken):
            continue
        per = "m2" if "m" in re.sub(r"[/\sna]", "", m.group("per")).lower() else "kg"
        davky.append({
            "text": re.sub(r"\s+", " ", m.group(0)).strip(), "typ": "jednoducha",
            "od": _num(m.group("od")), "do": _num(m.group("do")),
            "jednotka": m.group("jednotka"), "na": per,
            "za_den": bool(m.group("perday")), "interval": _interval(m.end()),
            "pozice": m.start(), "veta": re.sub(r"\s+", " ", _sentence_around(text42, m.start(), m.end())),
        })
    davky.sort(key=lambda d: d["pozice"])
    return {"podnadpisy": flags, "davky_na_hmotnost": davky}


def parse_spc(text: str) -> dict:
    text = normalize_text(text)
    pos = find_headings(text)
    sections = slice_sections(text, pos)
    missing = [k for k in WANTED_SECTIONS if k not in sections or not sections[k]]
    res = {"sekce": sections, "chybi": missing, "nalezene_nadpisy": sorted(pos, key=lambda k: pos[k][0])}
    m = re.search(r"(?i)sp\.?\s*zn\.?\s*:?\s*(sukls\d+/\d{4}[^\n]*)", text[:2000])
    if m:
        res["sp_zn"] = m.group(1).strip()
    if "4.2" in sections:
        res["analyza_42"] = analyze_42(sections["4.2"])
    if "1" in pos and "2" in pos:
        res["nazev_spc"] = re.sub(r"\s*\n\s*", " | ", text[pos["1"][1]:pos["2"][0]].strip())[:300]
    return res


EMA_ANNEX2_RE = re.compile(r"(?im)^[ \t]*P[RŘ][IÍ]LOHA\s+II\b")
EMA_H1_RE = _heading_regex(r"1", r"N[AÁ]ZEV\s+P[RŘ][IÍ]PRAVKU")


def parse_ema(text: str) -> list[dict]:
    """EMA 'product information' (CS) = PŘÍLOHA I (jeden nebo více SPC) + PŘÍLOHA II + PŘÍLOHA III (obaly, PIL).
    Uřízne vše od PŘÍLOHA II a každý blok začínající '1. NÁZEV PŘÍPRAVKU' parsuje jako samostatné SPC."""
    text = normalize_text(text)
    plain = strip_diacritics_keep_len(text)
    m2 = EMA_ANNEX2_RE.search(plain)
    cut = text[:m2.start()] if m2 else text
    plain_cut = plain[:len(cut)]
    starts = [m.start() for m in EMA_H1_RE.finditer(plain_cut)]
    # falešné starty: '1. NÁZEV PŘÍPRAVKU' se může objevit i v obsahu – bereme jen bloky, kde následuje sekce 2 do 3 000 znaků
    blocks = []
    for i, a in enumerate(starts):
        b = starts[i + 1] if i + 1 < len(starts) else len(cut)
        if b - a < 500:
            continue
        blocks.append(cut[a:b])
    if not blocks:
        blocks = [cut]
    out = []
    for i, blk in enumerate(blocks):
        parsed = parse_spc(blk)
        parsed["cast"] = i + 1
        out.append(parsed)
    return out


# ----------------------------------------------------------------------------
# DLP načtení
# ----------------------------------------------------------------------------

class DLP:
    def __init__(self, zip_path: Path):
        self.zip_path = zip_path
        self.tables: dict[str, list[dict]] = {}
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                name = Path(info.filename).name.lower()
                if name.endswith(".csv"):
                    self.tables[name[:-4]] = read_csv_bytes(z.read(info))
        log(f"DLP: načteno {len(self.tables)} tabulek: {', '.join(sorted(self.tables))}")

    def t(self, name: str) -> list[dict]:
        if name not in self.tables:
            raise KeyError(f"v DLP zipu chybí tabulka {name}.csv (jsou: {sorted(self.tables)})")
        return self.tables[name]


def build_product_index(dlp: DLP) -> dict:
    lp = dlp.t("dlp_lecivepripravky")
    docs = {r["KOD_SUKL"]: r for r in dlp.t("dlp_nazvydokumentu")}
    stavy = {r["REG"]: r["NAZEV"] for r in dlp.tables.get("dlp_stavyreg", [])}
    typy = {r["TYP_LP"]: r["NAZEV"] for r in dlp.tables.get("dlp_typlp", [])}
    formy = {r["FORMA"]: r["NAZEV"] for r in dlp.tables.get("dlp_formy", [])}
    cesty = {r["CESTA"]: r["NAZEV"] for r in dlp.tables.get("dlp_cesty", [])}
    atc = {r["ATC"]: r["NAZEV"] for r in dlp.tables.get("dlp_atc", [])}
    # dlp_lecivelatky je podmnožina; některé kódy ze složení jsou jen v dlp_latky -> sloučit
    latky = {r["KOD_LATKY"]: r for r in dlp.tables.get("dlp_latky", [])}
    latky.update({r["KOD_LATKY"]: r for r in dlp.t("dlp_lecivelatky")})
    soli = {r["KOD_SOLI"]: r["KOD_LATKY"] for r in dlp.tables.get("dlp_soli", [])}
    priznaky = {r["S"]: r["VYZNAM"] for r in dlp.tables.get("dlp_slozenipriznak", [])}
    platnost = dlp.tables.get("dlp_platnost", [{}])[0] if dlp.tables.get("dlp_platnost") else {}

    # Které příznaky složení = léčivá látka? Rozhodujeme podle číselníku, ne z hlavy.
    # L = "Léčivá látka", O = "Účinná látka, která odpovídá jiné účinné látce" (řádek 'odpovídá' – báze soli).
    # Rozpoznáváme podle textu číselníku, fallback na L/O. Použité příznaky se vypisují do statistiky.
    active_flags = {s for s, v in priznaky.items()
                    if re.search(r"(l[ée][čc]iv|[úu][čc]inn)[áa]\s+l[áa]tk", v.lower()) and "pomocn" not in v.lower()}
    if not active_flags:
        active_flags = {"L", "O"}

    slozeni: dict[str, list[dict]] = defaultdict(list)
    for r in dlp.t("dlp_slozeni"):
        if r["S"] in active_flags:
            slozeni[r["KOD_SUKL"]].append(r)

    # synonyma látek (pro vyhledávání)
    syn: dict[str, set[str]] = defaultdict(set)
    for r in dlp.tables.get("dlp_synonyma", []):
        if r.get("NAZEV"):
            syn[r["KOD_LATKY"]].add(r["NAZEV"])

    products = {}
    for r in lp:
        kod = r["KOD_SUKL"]
        d = docs.get(kod, {})
        spc_ref = d.get("SPC", "")
        # kódy léčivých látek tak, jak je uvádí SÚKL (řádky L + O). dlp_soli se NEPOUŽÍVÁ –
        # ověřeno, že obsahuje i "příbuzné" látky (dexibuprofen -> ibuprofen, estery, deriváty),
        # což by slévalo různé látky. Seskupení dělá ATC.
        base_codes = []
        for s in slozeni.get(kod, []):
            if s["KOD_LATKY"] not in base_codes:
                base_codes.append(s["KOD_LATKY"])
        products[kod] = {
            "kod_sukl": kod,
            "nazev": r.get("NAZEV", ""),
            "nazev_reg": r.get("NAZEV_REG", ""),
            "doplnek": r.get("DOPLNEK", ""),
            "sila": r.get("SILA", ""),
            "forma": r.get("FORMA", ""),
            "forma_nazev": formy.get(r.get("FORMA", ""), ""),
            "cesta": r.get("CESTA", ""),
            "cesta_nazev": cesty.get(r.get("CESTA", ""), ""),
            "baleni": r.get("BALENI", ""),
            "reg": r.get("REG", ""),
            "reg_nazev": stavy.get(r.get("REG", ""), ""),
            "rc": r.get("RC", ""),
            "typ_lp": r.get("TYP_LP", ""),
            "typ_lp_nazev": typy.get(r.get("TYP_LP", ""), ""),
            "atc": r.get("ATC_WHO", ""),
            "atc_nazev": atc.get(r.get("ATC_WHO", ""), ""),
            "dodavky": r.get("DODAVKY", ""),
            "vydej": r.get("VYDEJ", ""),
            "spc_ref": spc_ref,
            "dat_roz_spc": d.get("DAT_ROZ_SPC", ""),
            "latky_kody": base_codes,
            "latky_slozeni": [{"kod": s["KOD_LATKY"], "amnt": s.get("AMNT", ""), "un": s.get("UN", "")}
                              for s in slozeni.get(kod, [])],
        }
    return {
        "products": products, "latky": latky, "syn": syn, "atc": atc,
        "stavy": stavy, "typy": typy, "priznaky": priznaky, "active_flags": sorted(active_flags),
        "platnost": platnost,
    }


# ----------------------------------------------------------------------------
# Hlavní běh
# ----------------------------------------------------------------------------

def classify_spc_ref(ref: str) -> str:
    if not ref:
        return "chybi"
    if re.match(r"(?i)^https?://", ref):
        return "url_ema" if ("ema.europa.eu" in ref.lower() or "ec.europa.eu" in ref.lower()) else "url_jine"
    return "soubor"


class SpcZip:
    """Čtení jednotlivých souborů přímo z (velkého) zipu bez rozbalení."""
    def __init__(self, path: Path):
        self.z = zipfile.ZipFile(path)
        self.index: dict[str, str] = {}
        for n in self.z.namelist():
            base = Path(n).name
            self.index[base.lower()] = n
            self.index[Path(base).stem.lower()] = n  # i bez přípony
        log(f"SPC zip: {len(self.z.namelist())} souborů")

    def find(self, ref: str) -> str | None:
        r = ref.strip().lower()
        return self.index.get(r) or self.index.get(Path(r).stem)

    def read(self, member: str) -> bytes:
        return self.z.read(member)


def run(args: argparse.Namespace) -> None:
    raw = Path(args.raw_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    dlp_zip = Path(args.dlp_zip) if args.dlp_zip else _latest(raw, "DLP*.zip")
    spc_zip = Path(args.spc_zip) if args.spc_zip else (_latest(raw, "SPC*.zip") or Path("SPC-neni.zip"))
    if not dlp_zip or not dlp_zip.exists():
        sys.exit("Chybí DLP zip. Spusť nejdřív `python sukl_etl.py download` nebo zadej --dlp-zip.")
    log(f"DLP zip: {dlp_zip}")
    dlp = DLP(dlp_zip)
    idx = build_product_index(dlp)
    products: dict[str, dict] = idx["products"]

    stats: dict = {
        "spusteno": dt.datetime.now().isoformat(timespec="seconds"),
        "dlp_zip": dlp_zip.name, "spc_zip": spc_zip.name,
        "platnost": idx["platnost"],
        "priznaky_slozeni": idx["priznaky"], "priznaky_pouzite_jako_lecive": idx["active_flags"],
        "pripravky_celkem_v_dlp": len(products),
        "rozlozeni_reg": dict(Counter(f"{p['reg']} – {p['reg_nazev']}" for p in products.values())),
        "rozlozeni_typ_lp": dict(Counter(f"{p['typ_lp']} – {p['typ_lp_nazev']}" for p in products.values())),
        "rozlozeni_odkaz_spc": dict(Counter(classify_spc_ref(p["spc_ref"]) for p in products.values())),
    }

    # ---- výběr přípravků ----------------------------------------------------
    selected = list(products.values())
    filters = []
    if not args.all_reg:
        selected = [p for p in selected if p["reg"] == args.reg]
        filters.append(f"REG == {args.reg}")
    if not args.include_pzlu:
        before = len(selected)
        selected = [p for p in selected if "potravin" not in p["typ_lp_nazev"].lower()]
        filters.append(f"bez PZLÚ (-{before - len(selected)})")
    if args.only_supplied:
        selected = [p for p in selected if p["dodavky"].strip() == "1"]  # ověřeno: hodnoty 0/1
        filters.append("jen DODAVKY (dodáváno posl. 6 měs.)")
    if args.codes:
        want = {c.strip() for c in args.codes.split(",") if c.strip()}
        selected = [p for p in selected if p["kod_sukl"] in want]
        filters.append(f"kódy: {sorted(want)}")
    if args.name:
        q = strip_diacritics_keep_len(args.name.lower())
        selected = [p for p in selected if q in strip_diacritics_keep_len((p["nazev"] + " " + p["nazev_reg"]).lower())]
        filters.append(f"název obsahuje '{args.name}'")
    if args.atc_prefix:
        pref = tuple(x.strip().upper() for x in args.atc_prefix.split(","))
        selected = [p for p in selected if p["atc"].upper().startswith(pref)]
        filters.append(f"ATC začíná {pref}")
    stats["filtry"] = filters
    stats["pripravky_po_filtru"] = len(selected)

    if args.scope == "supplied":
        before = len(selected)
        selected = [p for p in selected if p["dodavky"].strip() == "1"]
        filters.append(f"scope=supplied: jen DODAVKY=1 (-{before - len(selected)})")
        stats["filtry"] = filters
        stats["pripravky_po_filtru"] = len(selected)

    # skupiny podle SPC dokumentu (mnoho balení -> 1 dokument). Klíč = název souboru, nebo URL (EMA).
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for p in selected:
        kind = classify_spc_ref(p["spc_ref"])
        key = p["spc_ref"].strip() if kind in ("soubor", "url_ema", "url_jine") else f"__{kind}__"
        by_doc[key].append(p)
    local_docs = [k for k in by_doc if not k.startswith("__") and not k.startswith("http")]
    ema_docs = [k for k in by_doc if k.startswith("http") and classify_spc_ref(k) == "url_ema"]
    other_url_docs = [k for k in by_doc if k.startswith("http") and classify_spc_ref(k) == "url_jine"]
    stats["dokumenty_lokalni_po_filtru"] = len(local_docs)
    stats["dokumenty_ema_odkaz_po_filtru"] = len(ema_docs)
    stats["dokumenty_jiny_odkaz_po_filtru"] = {"pocet": len(other_url_docs), "priklady": other_url_docs[:5]}
    stats["pripravky_bez_spc_po_filtru"] = len(by_doc.get("__chybi__", []))
    stats["pripravky_s_ema_odkazem_po_filtru"] = sum(len(by_doc[k]) for k in ema_docs)

    if args.scope == "representative":
        # 1 reprezentativní SPC na (ATC, léková forma): přednost dodávaným, pak nejnovější rozhodnutí, pak nejvíc balení
        def _date(d: str) -> str:
            m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", d or "")
            return f"{m.group(3)}{m.group(2)}{m.group(1)}" if m else "00000000"
        combos: dict[tuple, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        for ref in local_docs:
            for p in by_doc[ref]:
                combos[(p["atc"], p["forma"])][ref].append(p)
        keep = set()
        for combo, refs in combos.items():
            best = max(refs, key=lambda r: (any(p["dodavky"] == "1" for p in refs[r]),
                                             max(_date(p["dat_roz_spc"]) for p in refs[r]), len(refs[r]), r))
            keep.add(best)
        stats["scope_representative"] = {"kombinaci_atc_forma": len(combos), "dokumentu_pred": len(local_docs),
                                         "dokumentu_po": len(keep)}
        local_docs = [r for r in local_docs if r in keep]
        filters.append(f"scope=representative: 1 SPC na ATC×forma ({len(local_docs)} dokumentů)")
        stats["filtry"] = filters

    if args.sample:
        rnd = random.Random(args.seed)
        rnd.shuffle(local_docs)
        local_docs = local_docs[:args.sample]
        rnd.shuffle(ema_docs)
        ema_docs = ema_docs[:max(1, args.sample // 5)]
        stats["vzorek_dokumentu"] = args.sample

    # ---- parsování SPC --------------------------------------------------------
    if args.dlp_only:
        # jen přehled z DLP (bez textů) – hodí se pro rychlé statistiky bez 2,5 GB zipu
        stats["dlp_only"] = True
        latky_only = build_substances({k: {} for k in by_doc}, by_doc, idx, selected)
        stats["skupiny_atc_celkem"] = len(latky_only)
        with open(out / "dlp_stats.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        with open(out / "dlp_skupiny.json", "w", encoding="utf-8") as f:
            json.dump(latky_only, f, ensure_ascii=False, indent=1)
        log(f"Hotovo (jen DLP): {out/'dlp_stats.json'}, {out/'dlp_skupiny.json'}")
        print_summary(stats)
        return
    if not spc_zip or not spc_zip.exists():
        sys.exit("Chybí SPC zip. Spusť `python sukl_etl.py download` nebo zadej --spc-zip.")
    spc = SpcZip(spc_zip)

    docs_out: dict[str, dict] = {}
    fail = Counter()
    fail_examples: dict[str, list[str]] = defaultdict(list)
    fmt = Counter()
    sec_ok = Counter()
    sec_missing = Counter()
    scan_docs: list[str] = []
    sizes = []
    t0 = time.time()
    for i, ref in enumerate(local_docs, 1):
        member = spc.find(ref)
        if not member:
            fail["soubor_v_zipu_nenalezen"] += 1
            fail_examples["soubor_v_zipu_nenalezen"].append(ref)
            continue
        try:
            data = spc.read(member)
            text, f, info = extract_text(member, data)
        except Exception as e:  # noqa
            fail["extrakce_textu_selhala"] += 1
            fail_examples["extrakce_textu_selhala"].append(f"{ref}: {type(e).__name__}: {e}")
            continue
        fmt[f] += 1
        # detekce skenu: prakticky žádný text
        pages = info.get("stran") or 1
        if len(text.strip()) < 200 * max(1, pages) * 0.25:
            scan_docs.append(ref)
            docs_out[ref] = {"format": f, "stav": "sken_nebo_bez_textu", "sekce": {}, "chybi": WANTED_SECTIONS,
                             "pripravky": _prods_brief(by_doc[ref])}
            continue
        parsed = parse_spc(text)
        for k in WANTED_SECTIONS:
            (sec_ok if k in parsed["sekce"] and parsed["sekce"][k] else sec_missing)[k] += 1
        stav = "ok" if not parsed["chybi"] else ("castecne" if len(parsed["chybi"]) < len(WANTED_SECTIONS) else "nic")
        if stav == "nic":
            fail["zadna_sekce_nenalezena"] += 1
            fail_examples["zadna_sekce_nenalezena"].append(f"{ref} (nalezené nadpisy: {parsed['nalezene_nadpisy'][:6]})")
        entry = {
            "format": f, "zdroj": "SUKL", "stav": stav, "sp_zn": parsed.get("sp_zn"), "nazev_spc": parsed.get("nazev_spc"),
            "sekce": parsed["sekce"], "chybi": parsed["chybi"],
            "analyza_42": parsed.get("analyza_42"),
            "pripravky": _prods_brief(by_doc[ref]),
            "text_znaku": len(text),
        }
        docs_out[ref] = entry
        sizes.append(sum(len(v) for v in parsed["sekce"].values()))
        if i % 200 == 0 or i == len(local_docs):
            el = time.time() - t0
            log(f"  {i}/{len(local_docs)} dokumentů, {el:.0f}s, ~{el/i*1000:.0f} ms/dok")

    # ---- EMA / EU dokumenty (stažené přes `download --ema`) ------------------
    ema_stats = {"odkazu": len(ema_docs), "pdf_nalezeno": 0, "pdf_chybi": 0, "spc_bloku": 0, "stav": Counter(),
                 "sekce_vytazeno": Counter(), "sekce_chybi": Counter(), "selhani_priklady": []}
    if not args.no_ema and ema_docs:
        ema_dir = raw / "ema"
        manifest = {}
        mf = ema_dir / "manifest.json"
        if mf.exists():
            manifest = json.loads(mf.read_text("utf-8"))
        for url in ema_docs:
            fn = manifest.get(url) or _ema_filename(url)
            path = ema_dir / fn
            if not path.exists():
                ema_stats["pdf_chybi"] += 1
                ema_stats.setdefault("chybejici_odkazy", []).append(url)
                continue
            ema_stats["pdf_nalezeno"] += 1
            try:
                text, f, info = extract_text(fn, path.read_bytes())
                parts = parse_ema(text)
            except Exception as e:  # noqa
                ema_stats["stav"]["extrakce_selhala"] += 1
                ema_stats["selhani_priklady"].append(f"{url}: {type(e).__name__}: {e}")
                continue
            prods = by_doc[url]
            for part in parts:
                key = f"{url}#{part['cast']}"
                # přiřazení balení k dílčímu SPC: podle síly v názvu SPC, jinak všechna
                nazev = (part.get("nazev_spc") or "").upper().replace(" ", "")
                mine = [p for p in prods if p["sila"] and p["sila"].upper().replace(" ", "") in nazev] if len(parts) > 1 else prods
                stav = "ok" if not part["chybi"] else ("castecne" if len(part["chybi"]) < len(WANTED_SECTIONS) else "nic")
                ema_stats["stav"][stav] += 1
                ema_stats["spc_bloku"] += 1
                for k in WANTED_SECTIONS:
                    (ema_stats["sekce_vytazeno"] if k in part["sekce"] and part["sekce"][k] else ema_stats["sekce_chybi"])[k] += 1
                docs_out[key] = {
                    "format": "pdf", "zdroj": "EMA", "url": url, "cast": part["cast"], "casti_celkem": len(parts),
                    "stav": stav, "sp_zn": None, "nazev_spc": part.get("nazev_spc"),
                    "sekce": part["sekce"], "chybi": part["chybi"], "analyza_42": part.get("analyza_42"),
                    "pripravky": _prods_brief(mine or prods), "text_znaku": len(text),
                }
                by_doc[key] = mine or prods
                sizes.append(sum(len(v) for v in part["sekce"].values()))
    if "chybejici_odkazy" in ema_stats:
        ema_stats["chybejici_odkazy"] = ema_stats["chybejici_odkazy"][:50]
    ema_stats["stav"] = dict(ema_stats["stav"]); ema_stats["sekce_vytazeno"] = dict(ema_stats["sekce_vytazeno"])
    ema_stats["sekce_chybi"] = dict(ema_stats["sekce_chybi"]); ema_stats["selhani_priklady"] = ema_stats["selhani_priklady"][:20]
    stats["ema"] = ema_stats

    # ---- seskupení podle ATC ------------------------------------------------
    latky_out = build_substances(docs_out, by_doc, idx, selected)

    # ---- statistika & výstupy -------------------------------------------------
    stats.update({
        "dokumenty_zpracovano": len(local_docs),
        "formaty": dict(fmt),
        "sekce_vytazeno": dict(sec_ok), "sekce_chybi": dict(sec_missing),
        "dokumenty_sken_nebo_bez_textu": len(scan_docs),
        "dokumenty_sken_seznam": scan_docs[:200],
        "dokumenty_stav": dict(Counter(d["stav"] for d in docs_out.values())),
        "selhani": dict(fail), "selhani_priklady": {k: v[:20] for k, v in fail_examples.items()},
        "skupiny_atc_celkem": len(latky_out),
        "atc_bez_jakehokoli_spc": len({p["atc"] for p in selected} - {g["atc"] for g in latky_out}),
        "dokumenty_s_davkou_na_kg_nebo_m2": sum(
            1 for d in docs_out.values() if d.get("analyza_42") and d["analyza_42"]["davky_na_hmotnost"]),
        "dokumenty_s_podnadpisy_42": dict(Counter(
            k for d in docs_out.values() if d.get("analyza_42")
            for k, v in d["analyza_42"]["podnadpisy"].items() if v)),
        "prumer_znaku_sekci_na_dokument": int(sum(sizes) / len(sizes)) if sizes else 0,
        "cas_s": int(time.time() - t0),
    })
    # projekce velikosti na celý dataset (jen orientačně, z průměru)
    if args.sample and sizes:
        stats["projekce_velikosti_MB_cely_dataset_nekomprimovano"] = round(
            stats["prumer_znaku_sekci_na_dokument"] * stats["dokumenty_lokalni_po_filtru"] / 2**20, 1)

    dataset = {
        "meta": {
            "schema": SCHEMA_VERSION,
            "zdroj": "SÚKL – otevřená data (opendata.sukl.cz): DLP + SPC",
            "dlp_zip": dlp_zip.name, "spc_zip": spc_zip.name,
            "platnost_od": idx["platnost"].get("PLATNOST_OD"),
            "platnost_do": idx["platnost"].get("PLATNOST_DO"),
            "vygenerovano": dt.datetime.now().date().isoformat(),
            "vzorek": bool(args.sample or args.codes or args.name or args.atc_prefix),
            "sekce_nazvy": SECTION_TITLES,
        },
        "skupiny": latky_out,
        "dokumenty": docs_out,
    }
    ds_path = out / ("dataset_sample.json" if dataset["meta"]["vzorek"] else "dataset.json")
    with open(ds_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, separators=(",", ":"))
    stats["vystup_json_MB"] = round(ds_path.stat().st_size / 2**20, 2)
    import gzip
    stats["vystup_json_gzip_MB"] = round(len(gzip.compress(ds_path.read_bytes(), 6)) / 2**20, 2)
    # kolik textu je mezi generiky doslova identické (potenciál deduplikace textů)
    uniq: dict[str, set] = defaultdict(set); tot = Counter()
    for d in docs_out.values():
        for k, v in d["sekce"].items():
            if v:
                tot[k] += 1
                uniq[k].add(hashlib.sha1(v.encode("utf-8")).hexdigest())
    stats["sekce_unikatni_texty"] = {k: f"{len(uniq[k])}/{tot[k]}" for k in WANTED_SECTIONS if tot[k]}
    with open(out / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    write_report(out, stats, docs_out, latky_out)
    log(f"Hotovo. Výstup: {ds_path} ({stats['vystup_json_MB']} MB), {out/'stats.json'}, {out/'report.md'}")
    print_summary(stats)


def _prods_brief(prods: list[dict]) -> list[dict]:
    keys = ["kod_sukl", "nazev", "sila", "forma", "forma_nazev", "cesta", "baleni", "reg", "rc", "atc",
            "dat_roz_spc", "latky_kody", "latky_slozeni", "dodavky"]
    return [{k: p[k] for k in keys} for p in prods]


def _is_name_like(syn: str) -> bool:
    """Synonyma z dlp_synonyma obsahují i CAS čísla a sumární vzorce – ty do vyhledávání nepatří."""
    if len(syn) > 45 or len(syn) < 3:
        return False
    if re.search(r"[\d()\[\]{}=/]", syn):  # CAS čísla, sumární vzorce, chemické názvy
        return False
    return sum(ch.isalpha() for ch in syn) >= len(syn) * 0.6


def build_substances(docs_out: dict, by_doc: dict, idx: dict, vsechny_pripravky: list[dict] | None = None) -> list[dict]:
    """Primární jednotka datové sady = ATC kód (7. úroveň, nebo kratší, pokud SÚKL nic
    přesnějšího neuvádí). To je 'účinná látka / ATC' ze zadání; rozliší enantiomery
    (ibuprofen vs dexibuprofen), fixní kombinace i cestu podání.

    Obchodní názvy, léčivé látky a počet balení se berou ze VŠECH přípravků daného ATC
    po filtru (vsechny_pripravky), ne jen z těch, jejichž SPC se dostalo do datové sady –
    jinak by při scope=representative zmizely z vyhledávání značky jako Augmentin nebo Esmeron.
    Dokumenty ve skupině jsou jen ty, které v datové sadě skutečně jsou."""
    latky = idx["latky"]
    groups: dict[str, dict] = {}

    def _g(atc: str) -> dict:
        return groups.setdefault(atc, {"latky": Counter(), "kody": set(), "obchodni_nazvy": set(),
                                       "dokumenty": set(), "pripravku": 0, "pripravku_v_datech": 0,
                                       "cesty": Counter(), "formy": Counter()})

    for p in (vsechny_pripravky or []):
        g = _g(p["atc"] or "BEZ-ATC")
        for c in p["latky_kody"]:
            g["kody"].add(c)
            g["latky"][(latky.get(c, {}).get("NAZEV") or latky.get(c, {}).get("NAZEV_INN") or f"látka {c}").strip()] += 1
        g["obchodni_nazvy"].add(p["nazev"])
        g["cesty"][p["cesta_nazev"] or p["cesta"]] += 1
        g["formy"][p["forma_nazev"] or p["forma"]] += 1
        g["pripravku"] += 1

    for ref, d in docs_out.items():
        for p in by_doc[ref]:
            g = _g(p["atc"] or "BEZ-ATC")
            g["dokumenty"].add(ref)
            g["pripravku_v_datech"] += 1
            if not vsechny_pripravky:
                for c in p["latky_kody"]:
                    g["kody"].add(c)
                    g["latky"][(latky.get(c, {}).get("NAZEV") or latky.get(c, {}).get("NAZEV_INN") or f"látka {c}").strip()] += 1
                g["obchodni_nazvy"].add(p["nazev"]); g["cesty"][p["cesta"]] += 1; g["pripravku"] += 1

    out = []
    for atc, g in groups.items():
        if not g["dokumenty"]:
            continue  # ATC bez jediného SPC v datové sadě by ve vyhledávání končilo slepou uličkou
        rodice = []
        for n in (1, 3, 4, 5):
            if atc and atc != "BEZ-ATC" and len(atc) > n and idx["atc"].get(atc[:n]):
                rodice.append({"kod": atc[:n], "nazev": idx["atc"][atc[:n]]})
        syn = set()
        for c in g["kody"]:
            syn.update(x for x in idx["syn"].get(c, ()) if _is_name_like(x))
            l = latky.get(c, {})
            for k in ("NAZEV", "NAZEV_INN", "NAZEV_EN"):
                if l.get(k):
                    syn.add(l[k].strip())
        latky_names = [n for n, _ in g["latky"].most_common()]
        out.append({
            "id": slug(atc),
            "atc": atc if atc != "BEZ-ATC" else "",
            "nazev": (idx["atc"].get(atc) or " + ".join(latky_names[:3]) or "bez ATC").strip(),
            "atc_rodice": rodice,
            "latky": latky_names,
            "synonyma": sorted(syn - set(latky_names)),
            "obchodni_nazvy": sorted(g["obchodni_nazvy"]),
            "cesty": [c for c, _ in g["cesty"].most_common(3) if c],
            "formy": [f for f, _ in g["formy"].most_common(3) if f],
            "dokumenty": sorted(g["dokumenty"]),
            "pripravku": g["pripravku"],
            "pripravku_v_datech": g["pripravku_v_datech"],
        })
    out.sort(key=lambda x: (x["atc"] or "~", x["nazev"].lower()))
    return out


def write_report(out: Path, stats: dict, docs_out: dict, latky: list[dict]) -> None:
    L = []
    L.append(f"# Report ETL – {stats['spusteno']}\n")
    L.append(f"Platnost DLP: {stats['platnost']}  \nZip: {stats['dlp_zip']} / {stats['spc_zip']}\n")
    L.append("## Výběr\n")
    L.append(f"- přípravků v DLP celkem: {stats['pripravky_celkem_v_dlp']}")
    L.append(f"- filtry: {stats['filtry']}")
    L.append(f"- přípravků po filtru: {stats['pripravky_po_filtru']}")
    L.append(f"- z toho s lokálním SPC souborem: {stats['dokumenty_lokalni_po_filtru']} dokumentů")
    L.append(f"- z toho **s odkazem na EMA (centralizovaná registrace, SPC NENÍ v SÚKL zipu)**: "
             f"{stats['pripravky_s_ema_odkazem_po_filtru']} přípravků / {stats['dokumenty_ema_odkaz_po_filtru']} odkazů")
    L.append(f"- bez jakéhokoli SPC: {stats['pripravky_bez_spc_po_filtru']} přípravků")
    L.append(f"- zpracováno dokumentů: {stats['dokumenty_zpracovano']}"
             + (f" (vzorek {stats['vzorek_dokumentu']})" if stats.get("vzorek_dokumentu") else ""))
    L.append("\n## Rozložení v celém DLP (před filtrem)\n")
    for k in ("rozlozeni_reg", "rozlozeni_typ_lp", "rozlozeni_odkaz_spc"):
        L.append(f"**{k}**")
        for a, b in sorted(stats[k].items(), key=lambda kv: -kv[1]):
            L.append(f"- {a}: {b}")
        L.append("")
    L.append(f"Příznaky složení v číselníku: {stats['priznaky_slozeni']}  ")
    L.append(f"Jako *léčivá látka* použity příznaky: {stats['priznaky_pouzite_jako_lecive']}\n")
    L.append("## Parsování\n")
    L.append(f"- formáty: {stats['formaty']}")
    L.append(f"- stav dokumentů: {stats['dokumenty_stav']}")
    L.append(f"- sken / bez textu: {stats['dokumenty_sken_nebo_bez_textu']}")
    L.append(f"- sekce vytaženy: {stats['sekce_vytazeno']}")
    L.append(f"- sekce chybí: {stats['sekce_chybi']}")
    L.append(f"- selhání: {stats['selhani']}")
    for k, v in stats["selhani_priklady"].items():
        L.append(f"  - {k}:")
        L.extend(f"    - {x}" for x in v)
    e = stats.get("ema", {})
    L.append(f"- EMA/EC: odkazů {e.get('odkazu')}, PDF nalezeno {e.get('pdf_nalezeno')}, chybí {e.get('pdf_chybi')}, "
             f"SPC bloků {e.get('spc_bloku')}, stav {e.get('stav')}, sekce chybí {e.get('sekce_chybi')}")
    for x in e.get("selhani_priklady", []):
        L.append(f"  - {x}")
    for x in e.get("chybejici_odkazy", []):
        L.append(f"  - PDF nestaženo: {x}")
    L.append(f"- dokumentů s výrazem dávky /kg nebo /m²: {stats['dokumenty_s_davkou_na_kg_nebo_m2']}")
    L.append(f"- dokumentů s podnadpisy v 4.2: {stats['dokumenty_s_podnadpisy_42']}")
    L.append(f"- skupin ATC (primární jednotka): {stats['skupiny_atc_celkem']}")
    L.append(f"- průměr znaků vybraných sekcí / dokument: {stats['prumer_znaku_sekci_na_dokument']}")
    if "projekce_velikosti_MB_cely_dataset_nekomprimovano" in stats:
        L.append(f"- **projekce velikosti celého datasetu (nekomprimováno, jen sekce):** "
                 f"~{stats['projekce_velikosti_MB_cely_dataset_nekomprimovano']} MB")
    L.append(f"- unikátní texty sekcí (unikátní/celkem): {stats['sekce_unikatni_texty']}")
    L.append(f"- výstupní JSON: {stats['vystup_json_MB']} MB (gzip {stats['vystup_json_gzip_MB']} MB), čas {stats['cas_s']} s\n")

    L.append("## Dokumenty s chybějícími sekcemi\n")
    for ref, d in sorted(docs_out.items()):
        if d["chybi"]:
            names = ", ".join(sorted({p['nazev'] for p in d['pripravky']}))[:80]
            L.append(f"- {ref} [{d['format']}] {names}: chybí {d['chybi']}")
    L.append("\n## Náhled vytažených sekcí (prvních 300 znaků; u plného běhu jen prvních 150 dokumentů)\n")
    for ref, d in sorted(docs_out.items())[:150] if len(docs_out) > 200 else sorted(docs_out.items()):
        names = ", ".join(sorted({p['nazev'] for p in d['pripravky']}))[:100]
        L.append(f"### {ref} [{d['format']}] – {names}\n")
        if d.get("nazev_spc"):
            L.append(f"1. NÁZEV PŘÍPRAVKU: {d['nazev_spc']}  ")
        if d.get("sp_zn"):
            L.append(f"sp. zn.: {d['sp_zn']}\n")
        for k in WANTED_SECTIONS:
            t = d["sekce"].get(k, "")
            L.append(f"**{k} {SECTION_TITLES[k]}** ({len(t)} zn.)  ")
            L.append("> " + (t[:300].replace("\n", " ") if t else "— CHYBÍ —") + "\n")
        a = d.get("analyza_42")
        if a:
            L.append(f"podnadpisy 4.2: {[k for k, v in a['podnadpisy'].items() if v]}  ")
            for dv in a["davky_na_hmotnost"][:8]:
                L.append(f"- dávka `{dv['text']}` ← „{dv['veta'][:160]}“")
            L.append("")
    (out / "report.md").write_text("\n".join(L), encoding="utf-8")


def print_summary(stats: dict) -> None:
    print("\n===== SOUHRN =====")
    for k in ("pripravky_celkem_v_dlp", "filtry", "pripravky_po_filtru", "dokumenty_lokalni_po_filtru",
              "pripravky_s_ema_odkazem_po_filtru", "pripravky_bez_spc_po_filtru", "dokumenty_zpracovano",
              "formaty", "dokumenty_stav", "dokumenty_sken_nebo_bez_textu", "sekce_vytazeno", "sekce_chybi",
              "selhani", "skupiny_atc_celkem", "dokumenty_s_davkou_na_kg_nebo_m2", "prumer_znaku_sekci_na_dokument",
              "projekce_velikosti_MB_cely_dataset_nekomprimovano", "sekce_unikatni_texty",
              "vystup_json_MB", "vystup_json_gzip_MB", "cas_s"):
        if k in stats:
            print(f"{k}: {stats[k]}")


def _latest(d: Path, glob: str) -> Path | None:
    files = sorted(d.glob(glob))
    return files[-1] if files else None


def _ema_filename(url: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", url.rsplit("/", 1)[-1]) or "ema.pdf"
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    return f"{hashlib.sha1(url.encode()).hexdigest()[:8]}_{base}"


def _ema_url_variants(url: str):
    """Varianty URL pro odkazy, které SÚKL uvádí špatně (ověřeno na 404 z běhu 09/2026):
    lomítka v názvu přípravku (efavirenz/emtricitabine/... -> spojeno pomlčkami),
    přípona -0 před .pdf, cesta amended-product-information místo product-information."""
    seen = [url]
    yield url
    m = re.match(r"(https://www\.ema\.europa\.eu/[a-z]{2}/documents/[a-z-]*product-information/)(.+)$", url)
    if m:
        head, tail = m.groups()
        cands = []
        if "/" in tail:
            cands.append(head + tail.replace("/", "-"))
        t2 = re.sub(r"-\d+(\.pdf)$", r"\1", tail)
        if t2 != tail:
            cands.append(head + t2)
            if "/" in t2:
                cands.append(head + t2.replace("/", "-"))
        if "amended-product-information" in head:
            h2 = head.replace("amended-product-information", "product-information")
            cands += [h2 + tail, h2 + tail.replace("/", "-")]
        for c in cands:
            if c not in seen:
                seen.append(c); yield c


def _get_ema_pdf(url: str) -> tuple[bytes, str]:
    """Stáhne PDF; při 404 zkusí opravené varianty URL. Vrací (data, skutečně použité URL)."""
    last = None
    for cand in _ema_url_variants(url):
        try:
            data = http_get(cand, timeout=120)
            if not data.startswith(b"%PDF"):
                raise RuntimeError(f"odpověď není PDF ({len(data)} B)")
            return data, cand
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (404, 410):
                raise
        except Exception as e:  # noqa
            last = e
            raise
    raise last  # type: ignore[misc]


def cmd_download_ema(args: argparse.Namespace) -> None:
    """Stáhne CS 'product information' PDF z EMA/EC pro všechny centralizovaně registrované přípravky (REG=R)."""
    raw = Path(args.raw_dir)
    dlp_zip = Path(args.dlp_zip) if args.dlp_zip else _latest(raw, "DLP*.zip")
    if not dlp_zip or not dlp_zip.exists():
        sys.exit("Chybí DLP zip (nejdřív `download`).")
    idx = build_product_index(DLP(dlp_zip))
    urls = sorted({p["spc_ref"].strip() for p in idx["products"].values()
                   if p["reg"] == args.reg and classify_spc_ref(p["spc_ref"]) == "url_ema"})
    ema_dir = raw / "ema"
    ema_dir.mkdir(parents=True, exist_ok=True)
    if args.only_failed:
        ff = ema_dir / "download_failures.txt"
        if not ff.exists():
            sys.exit(f"Nenalezen {ff} – není co opakovat.")
        want = {l.split(": ", 1)[0].strip() for l in ff.read_text("utf-8").splitlines() if l.strip()}
        urls = [u for u in urls if u in want]
        log(f"Opakuji jen {len(urls)} dříve neúspěšných odkazů.")
    mf = ema_dir / "manifest.json"
    manifest = json.loads(mf.read_text("utf-8")) if mf.exists() else {}
    log(f"EMA/EC odkazů: {len(urls)} (už staženo: {sum(1 for u in urls if (ema_dir / manifest.get(u, _ema_filename(u))).exists())})")
    fails = []
    delay = max(args.delay, 2.0)   # adaptivně: po 429 se prodlužuje, po sérii úspěchů zkracuje
    ok_streak = 0
    done_now = 0
    t0 = time.time()
    for i, url in enumerate(urls, 1):
        fn = manifest.get(url) or _ema_filename(url)
        path = ema_dir / fn
        if path.exists() and path.stat().st_size > 1000:
            manifest[url] = fn
            continue
        before429 = RATE["hits429"]
        try:
            data, used = _get_ema_pdf(url)
            if used != url:
                log(f"  odkaz opraven: {url.rsplit('/', 1)[-1]} -> {used.rsplit('/', 1)[-1]}")
            path.write_bytes(data)
            manifest[url] = fn
            done_now += 1
            ok_streak += 1
        except Exception as e:  # noqa
            ok_streak = 0
            fails.append(f"{url}: {type(e).__name__}: {e}")
            log(f"  SELHALO ({len(fails)}.): {url.rsplit('/', 1)[-1]}: {type(e).__name__}: {e}")
        if RATE["hits429"] > before429:
            delay = min(60.0, delay * 1.5); ok_streak = 0
            log(f"  server omezuje rychlost -> rozestup mezi požadavky {delay:.0f}s")
        elif ok_streak >= 20 and delay > args.delay:
            delay = max(args.delay, delay / 1.3); ok_streak = 0
        if i % 25 == 0 or done_now % 10 == 0:
            rate = done_now / max(1, time.time() - t0) * 3600
            log(f"  {i}/{len(urls)} (staženo nyní {done_now}, ~{rate:.0f}/h, selhání {len(fails)})")
            mf.write_text(json.dumps(manifest, ensure_ascii=False, indent=0), "utf-8")
        time.sleep(delay)
    mf.write_text(json.dumps(manifest, ensure_ascii=False, indent=0), "utf-8")
    (ema_dir / "download_failures.txt").write_text("\n".join(fails), "utf-8")
    total = sum((ema_dir / f).stat().st_size for f in manifest.values() if (ema_dir / f).exists())
    log(f"Hotovo: {len(manifest)} PDF ({total/2**20:.0f} MB), selhání {len(fails)} -> {ema_dir/'download_failures.txt'}")


def cmd_export(args: argparse.Namespace) -> None:
    """Z out/dataset.json vyrobí data pro aplikaci: gzipované shardy + manifest (do docs/data/)."""
    import gzip
    src = Path(args.dataset)
    if not src.exists():
        sys.exit(f"Nenalezen {src} – spusť nejdřív `run`.")
    ds = json.loads(src.read_text("utf-8"))
    dst = Path(args.app_data)
    dst.mkdir(parents=True, exist_ok=True)
    for old in dst.glob("*.json.gz"):
        old.unlink()
    # dokumenty: zkrácené klíče (URL -> hash) + stabilní pořadí
    docs = ds["dokumenty"]
    key_map = {}
    for k in docs:
        key_map[k] = k if not k.startswith("http") else "ema_" + hashlib.sha1(k.encode()).hexdigest()[:10]
    for g in ds["skupiny"]:
        g["dokumenty"] = [key_map[k] for k in g["dokumenty"] if k in key_map]
    items = sorted(docs.items())
    shard_bytes = args.shard_kb * 1024
    shards, cur, cur_size = [], {}, 0
    for k, v in items:
        v = dict(v)
        v["id"] = key_map[k]
        if k.startswith("http"):
            v["url"] = k.split("#")[0]
        v.pop("text_znaku", None)
        blob = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
        if cur and cur_size + len(blob) > shard_bytes:
            shards.append(cur); cur, cur_size = {}, 0
        cur[v["id"]] = v; cur_size += len(blob)
    if cur:
        shards.append(cur)
    manifest = {"schema": SCHEMA_VERSION, "meta": ds["meta"], "vygenerovano": dt.datetime.now().isoformat(timespec="seconds"),
                "skupin": len(ds["skupiny"]), "dokumentu": len(docs), "soubory": []}

    def _write(name: str, obj) -> dict:
        raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        gz = gzip.compress(raw, 9)
        (dst / name).write_bytes(gz)
        return {"soubor": name, "bajtu": len(gz), "bajtu_raw": len(raw), "sha1": hashlib.sha1(gz).hexdigest()[:12]}

    manifest["index"] = _write("index.json.gz", {"skupiny": ds["skupiny"]})
    for i, sh in enumerate(shards):
        manifest["soubory"].append({**_write(f"docs-{i:03d}.json.gz", sh), "dokumentu": len(sh)})
    manifest["verze"] = hashlib.sha1((manifest["index"]["sha1"] + "".join(f["sha1"] for f in manifest["soubory"])).encode()).hexdigest()[:12]
    (dst / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
    total = manifest["index"]["bajtu"] + sum(f["bajtu"] for f in manifest["soubory"])
    log(f"Export: {len(ds['skupiny'])} skupin, {len(docs)} dokumentů, {len(shards)} shardů, celkem {total/2**20:.1f} MB gzip -> {dst}")


def cmd_download(args: argparse.Namespace) -> None:
    raw = Path(args.raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    dlp_links = find_zip_links(CATALOG_DLP, r"DLP\d{8}\.zip")
    spc_links = find_zip_links(CATALOG_SPC, r"SPC\d{8}\.zip")
    if not dlp_links or not spc_links:
        sys.exit(f"Nenašel jsem odkazy na zipy v katalogu (DLP: {dlp_links}, SPC: {spc_links}). "
                 "Struktura stránky se možná změnila – stáhni ručně a zadej --dlp-zip/--spc-zip.")
    log(f"DLP: {dlp_links[-1]}")
    log(f"SPC: {spc_links[-1]} (POZOR: ~2,5 GB)")
    for url in (dlp_links[-1], spc_links[-1]):
        dest = raw / url.rsplit("/", 1)[-1]
        if dest.exists() and not args.force:
            log(f"  už existuje: {dest}")
            continue
        download_file(url, dest)
    iface = find_zip_links(CATALOG_DLP, r"DLP_datove_rozhrani\d*\.csv")
    if iface:
        (raw / iface[-1].rsplit("/", 1)[-1]).write_bytes(http_get(iface[-1]))
        log(f"  datové rozhraní: {iface[-1]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", default="data_raw", help="kam se ukládají stažené zipy")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("download", help="stáhne aktuální DLP a SPC zip z opendata.sukl.cz")
    d.add_argument("--force", action="store_true")
    e = sub.add_parser("download-ema", help="stáhne CS SPC (product information) z EMA/EC pro centralizovaně registrované přípravky")
    e.add_argument("--dlp-zip"); e.add_argument("--reg", default="R"); e.add_argument("--delay", type=float, default=2.0)
    e.add_argument("--only-failed", action="store_true", help="zkusit znovu jen odkazy z ema/download_failures.txt")
    x = sub.add_parser("export", help="vyrobí z out/dataset.json data pro aplikaci (docs/data/)")
    x.add_argument("--dataset", default="out/dataset.json")
    x.add_argument("--app-data", default="../docs/data")
    x.add_argument("--shard-kb", type=int, default=1500, help="cílová velikost shardu (nekomprimovaně)")
    r = sub.add_parser("run", help="spustí ETL")
    r.add_argument("--dlp-zip"); r.add_argument("--spc-zip")
    r.add_argument("--out-dir", default="out")
    r.add_argument("--sample", type=int, help="náhodný vzorek N SPC dokumentů")
    r.add_argument("--seed", type=int, default=42)
    r.add_argument("--codes", help="čárkou oddělené SÚKL kódy")
    r.add_argument("--name", help="podřetězec názvu přípravku (bez ohledu na diakritiku)")
    r.add_argument("--atc-prefix", help="čárkou oddělené prefixy ATC (např. N02,J01)")
    r.add_argument("--reg", default="R", help="stav registrace, který se bere (výchozí R)")
    r.add_argument("--all-reg", action="store_true", help="nefiltrovat podle stavu registrace")
    r.add_argument("--include-pzlu", action="store_true", help="zahrnout i potraviny pro zvl. lék. účely")
    r.add_argument("--only-supplied", action="store_true", help="jen přípravky dodávané v posl. 6 měsících (DODAVKY=1)")
    r.add_argument("--dlp-only", action="store_true", help="jen statistika z DLP, bez SPC zipu")
    r.add_argument("--scope", choices=["all", "supplied", "representative"], default="representative",
                   help="all = všechny SPC; supplied = jen přípravky dodávané v posl. 6 měs.; "
                        "representative = 1 SPC na ATC×léková forma (EMA dokumenty vždy všechny)")
    r.add_argument("--no-ema", action="store_true", help="nezpracovávat EMA/EC dokumenty")
    args = ap.parse_args()
    if args.cmd == "download":
        cmd_download(args)
    elif args.cmd == "download-ema":
        cmd_download_ema(args)
    elif args.cmd == "export":
        cmd_export(args)
    else:
        run(args)


if __name__ == "__main__":
    main()
