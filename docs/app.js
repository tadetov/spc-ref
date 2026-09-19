/* SPC – offline referenční texty SÚKL/EMA. Vanilla JS, žádné externí knihovny.
   Zásada: aplikace nic negeneruje – zobrazuje text SPC, u každého bloku je zdroj. */
"use strict";

const APP_VERSION = "0.2.1";
const DATA_BASE = "./data/";
const STALE_DAYS = 92; // > 3 měsíce od konce platnosti dat
const SEKCE = ["2", "4.1", "4.2", "4.3", "4.4", "4.5", "4.6"];

// ---------------------------------------------------------------- utils
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** Odstraní diakritiku se ZACHOVÁNÍM délky (1 znak -> 1 znak), aby pozice seděly do původního textu. */
function fold(s) {
  let out = "";
  for (const ch of s) {
    if (ch.length > 1) { out += ch; continue; } // znaky mimo BMP: nechat, zachovat délku
    const d = ch.normalize("NFD");
    const base = d[0];
    out += /\p{M}/u.test(base) ? ch : base;
  }
  return out.toLowerCase();
}
const norm = (s) => fold(String(s || "")).replace(/[^a-z0-9%]+/g, " ").trim();

function parseCzDate(s) {
  const m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(s || "");
  if (m) return new Date(+m[3], +m[2] - 1, +m[1]);
  const m2 = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || "");
  return m2 ? new Date(+m2[1], +m2[2] - 1, +m2[3]) : null;
}
const fmtDate = (d) => d ? `${d.getDate()}. ${d.getMonth() + 1}. ${d.getFullYear()}` : "?";
const fmtNum = (x) => {
  if (x == null || !isFinite(x)) return "?";
  const r = Math.abs(x) >= 100 ? Math.round(x) : Math.abs(x) >= 10 ? Math.round(x * 10) / 10 : Math.round(x * 100) / 100;
  return String(r).replace(".", ",");
};

// ---------------------------------------------------------------- IndexedDB
const DB_NAME = "spcref", DB_VER = 1;
let dbp = null;
function db() {
  if (dbp) return dbp;
  dbp = new Promise((res, rej) => {
    const r = indexedDB.open(DB_NAME, DB_VER);
    r.onupgradeneeded = () => {
      const d = r.result;
      if (!d.objectStoreNames.contains("kv")) d.createObjectStore("kv");
      if (!d.objectStoreNames.contains("docs")) d.createObjectStore("docs");
    };
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });
  return dbp;
}
async function kvGet(k) { const d = await db(); return new Promise((res, rej) => { const t = d.transaction("kv").objectStore("kv").get(k); t.onsuccess = () => res(t.result); t.onerror = () => rej(t.error); }); }
async function kvSet(k, v) { const d = await db(); return new Promise((res, rej) => { const tx = d.transaction("kv", "readwrite"); tx.objectStore("kv").put(v, k); tx.oncomplete = res; tx.onerror = () => rej(tx.error); }); }
async function docGet(id) { const d = await db(); return new Promise((res, rej) => { const t = d.transaction("docs").objectStore("docs").get(id); t.onsuccess = () => res(t.result); t.onerror = () => rej(t.error); }); }
async function docsPut(map) { const d = await db(); return new Promise((res, rej) => { const tx = d.transaction("docs", "readwrite"); const st = tx.objectStore("docs"); for (const [k, v] of Object.entries(map)) st.put(v, k); tx.oncomplete = res; tx.onerror = () => rej(tx.error); }); }
async function docsClear() { const d = await db(); return new Promise((res, rej) => { const tx = d.transaction("docs", "readwrite"); tx.objectStore("docs").clear(); tx.oncomplete = res; tx.onerror = () => rej(tx.error); }); }

// ---------------------------------------------------------------- data loading
const state = { manifest: null, groups: [], byId: new Map(), index: [], docsLoaded: false, loading: false, user: { fav: [], hist: [], xr: [] } };

async function fetchGz(name) {
  const r = await fetch(DATA_BASE + name, { cache: "no-store" });
  if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`);
  if (!("DecompressionStream" in window)) throw new Error("Prohlížeč neumí DecompressionStream (potřeba iOS 16.4+ / Safari 16.4+).");
  const ds = new DecompressionStream("gzip");
  return new Response(r.body.pipeThrough(ds)).json();
}

async function loadFromStore() {
  const [manifest, groups, user] = await Promise.all([kvGet("manifest"), kvGet("groups"), kvGet("user")]);
  if (user) state.user = Object.assign({ fav: [], hist: [], xr: [] }, user);
  if (manifest && groups) {
    state.manifest = manifest; setGroups(groups);
    const loaded = (await kvGet("shards_loaded")) || [];
    state.docsLoaded = loaded.length === manifest.soubory.length;
    return true;
  }
  return false;
}

function setGroups(groups) {
  state.groups = groups;
  state.byId = new Map(groups.map((g) => [g.id, g]));
  state.index = groups.map((g) => {
    const terms = [g.nazev, g.atc, ...(g.latky || []), ...(g.obchodni_nazvy || []), ...(g.synonyma || [])].filter(Boolean);
    const seen = new Set();
    const t = [];
    for (const raw of terms) { const n = norm(raw); if (n && !seen.has(n)) { seen.add(n); t.push({ n, raw, words: n.split(" ") }); } }
    return { g, terms: t, pop: g.pripravku || 1 };
  });
}

/** Stáhne manifest + index + shardy, zapisuje do IndexedDB po dávkách s ukazatelem postupu. */
async function downloadData(onProgress, { force = false } = {}) {
  if (state.loading) return;
  state.loading = true;
  try {
    const mr = await fetch(DATA_BASE + "manifest.json", { cache: "no-store" });
    if (!mr.ok) throw new Error(`manifest.json: HTTP ${mr.status}`);
    const manifest = await mr.json();
    const old = await kvGet("manifest");
    let loaded = (await kvGet("shards_loaded")) || [];
    if (force || !old || old.verze !== manifest.verze) {
      await docsClear(); loaded = []; await kvSet("shards_loaded", loaded);
    }
    onProgress({ step: "index", done: 0, total: manifest.soubory.length + 1 });
    const idx = await fetchGz(manifest.index.soubor);
    await kvSet("groups", idx.skupiny); await kvSet("manifest", manifest);
    state.manifest = manifest; setGroups(idx.skupiny);
    let i = 0;
    for (const f of manifest.soubory) {
      i++;
      if (loaded.includes(f.soubor)) { onProgress({ step: f.soubor, done: i, total: manifest.soubory.length + 1 }); continue; }
      const shard = await fetchGz(f.soubor);
      await docsPut(shard);
      loaded.push(f.soubor); await kvSet("shards_loaded", loaded);
      onProgress({ step: f.soubor, done: i, total: manifest.soubory.length + 1 });
    }
    state.docsLoaded = true;
    onProgress({ step: "hotovo", done: manifest.soubory.length + 1, total: manifest.soubory.length + 1 });
  } finally { state.loading = false; }
}

async function checkForUpdate() {
  try {
    const r = await fetch(DATA_BASE + "manifest.json", { cache: "no-store" });
    if (!r.ok) return null;
    const m = await r.json();
    return (state.manifest && m.verze !== state.manifest.verze) ? m : null;
  } catch { return null; }
}

// ---------------------------------------------------------------- search (in memory)
function editDistance(a, b, max) {
  if (Math.abs(a.length - b.length) > max) return max + 1;
  const prev = new Array(b.length + 1).fill(0).map((_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let cur = [i]; let rowMin = i;
    for (let j = 1; j <= b.length; j++) {
      const v = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      cur.push(v); if (v < rowMin) rowMin = v;
    }
    if (rowMin > max) return max + 1;
    prev.splice(0, prev.length, ...cur);
  }
  return prev[b.length];
}

/** Levné skóre bez editační vzdálenosti. Vrací null, když token neodpovídá. */
function cheapScore(t, qt, isFirstTerm) {
  if (t.n === qt) return isFirstTerm ? 0 : 1;
  if (t.n.startsWith(qt)) return isFirstTerm ? 1 : 2;
  if (t.words.length > 1 && t.words.some((w) => w.startsWith(qt))) return 3;
  if (qt.length >= 4 && t.n.includes(qt)) return 4;
  return null;
}

function scan(qtoks, fuzzy) {
  const out = [];
  for (const e of state.index) {
    let score = 0, hit = null;
    for (const qt of qtoks) {
      let best = Infinity, bestTerm = null;
      for (let i = 0; i < e.terms.length; i++) {
        const t = e.terms[i];
        let sc = cheapScore(t, qt, i === 0);
        if (sc == null && fuzzy && qt.length >= 4) {
          const maxd = qt.length >= 8 ? 2 : 1;
          let dmin = maxd + 1;
          for (const w of t.words) { if (Math.abs(w.length - qt.length) <= maxd) { const d = editDistance(qt, w, maxd); if (d < dmin) dmin = d; } }
          if (dmin <= maxd) sc = 5 + dmin;
        }
        if (sc != null && sc < best) { best = sc; bestTerm = t; if (best === 0) break; }
      }
      if (bestTerm == null) { score = Infinity; break; }
      score += best;
      if (!hit || best < hit.s) hit = { s: best, t: bestTerm };
    }
    if (score < Infinity) out.push({ g: e.g, score, via: hit.t.raw, pop: e.pop });
  }
  // shoda stejně dobrá u více skupin (např. IBUPROFEN systémový vs. kožní vs. i.v.):
  // rozhoduje počet balení na trhu, ne abeceda
  out.sort((a, b) => a.score - b.score || b.pop - a.pop || a.g.nazev.localeCompare(b.g.nazev, "cs"));
  return out;
}

function search(q, limit = 30) {
  const qn = norm(q);
  if (!qn) return [];
  const qtoks = qn.split(" ");
  let out = scan(qtoks, false);
  if (out.length < 3) out = scan(qtoks, true);   // překlepy řešíme, až když levný průchod nic nenajde
  return out.slice(0, limit);
}

// ---------------------------------------------------------------- user data
async function saveUser() { await kvSet("user", state.user); }
function isFav(id) { return state.user.fav.includes(id); }
async function toggleFav(id) { const f = state.user.fav; const i = f.indexOf(id); if (i >= 0) f.splice(i, 1); else f.unshift(id); await saveUser(); }
async function pushHist(id) { const h = state.user.hist.filter((x) => x !== id); h.unshift(id); state.user.hist = h.slice(0, 25); await saveUser(); }

// ---------------------------------------------------------------- text rendering
/** Text SPC z PDF má konce řádků na každém řádku. Pro čtení: prázdný řádek = odstavec,
    odrážky zůstávají na vlastním řádku, krátký řádek bez tečky = podnadpis. Text se nemění, jen zalomení. */
function renderSpcText(text, highlighter) {
  if (!text) return '<p class="empty">Tato sekce v SPC není (parser ji v dokumentu nenašel).</p>';
  const H = highlighter || esc;
  const lines = text.split("\n").map((l) => l.trim());
  const BUL = /^[•\-–●▪◦*]\s*/;
  const lower = /^[a-zá-ž(]/;
  let html = "", buf = [], bullets = [], lastSub = false;
  const flush = () => { if (buf.length) { html += `<p>${H(buf.join(" "))}</p>`; buf = []; lastSub = false; } };
  const flushB = () => { const b = bullets.filter(Boolean); if (b.length) html += `<ul class="bullets">${b.map((x) => `<li>${H(x)}</li>`).join("")}</ul>`; bullets = []; lastSub = false; };
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (!l) { flush(); continue; }                       // prázdný řádek = konec odstavce (odrážky zůstávají otevřené)
    if (BUL.test(l)) {                                    // odrážka; "•" na samostatném řádku čeká na obsah
      flush();
      const c = l.replace(BUL, "");
      if (bullets.length && bullets[bullets.length - 1] === "") bullets[bullets.length - 1] = c; else bullets.push(c);
      continue;
    }
    if (bullets.length) {
      if (bullets[bullets.length - 1] === "") { bullets[bullets.length - 1] = l; continue; }
      if (lower.test(l)) { bullets[bullets.length - 1] += " " + l; continue; }
      flushB();
    }
    const next = lines.slice(i + 1).find(Boolean);
    const isSub = !buf.length && !lastSub && next && l.length <= 80 && !/[.;,]$/.test(l) && /^[A-ZÁ-Ž]/.test(l) && !/^\d/.test(l) && !/[.!?]\s+\S/.test(l);
    if (isSub) { html += `<div class="subhead">${H(l)}</div>`; lastSub = true; continue; }
    buf.push(l);
  }
  flush(); flushB();
  return html;
}

/** Odstavce sekce 4.2 obsahující některé z klíčových slov (jen výběr textu, nic víc). */
function paragraphsMatching(text, re) {
  if (!text) return [];
  const paras = [];
  let cur = [];
  for (const raw of text.split("\n")) {
    const l = raw.trim();
    const isSub = l && l.length <= 80 && !/[.;,]$/.test(l) && /^[A-ZÁ-Ž]/.test(l) && !/^\d/.test(l);
    if (!l || isSub) { if (cur.length) paras.push(cur.join("\n")); cur = []; if (isSub) cur.push(l); continue; }
    cur.push(l);
  }
  if (cur.length) paras.push(cur.join("\n"));
  return paras.filter((p) => re.test(fold(p)));
}

// ---------------------------------------------------------------- views
const IS_BROWSER = typeof document !== "undefined";
const view = IS_BROWSER ? $("#view") : null;
function setView(html) {
  view.innerHTML = html;
  // Při psaní do vyhledávacího pole se nesmí přebírat fokus – iOS by zavřel klávesnici.
  if (document.activeElement === document.getElementById("q")) return;
  view.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}
function sourceStrip(doc) {
  if (doc.zdroj === "EMA") {
    const part = doc.casti_celkem > 1 ? ` (SPC ${doc.cast} z ${doc.casti_celkem} v dokumentu)` : "";
    return `<div class="source">Zdroj: <b>EMA – Souhrn údajů o přípravku (CS)</b>${part}. <a href="${esc(doc.url)}" target="_blank" rel="noopener">Originál PDF</a></div>`;
  }
  const spz = doc.sp_zn ? ` · sp. zn. ${esc(doc.sp_zn)}` : "";
  const dat = doc.pripravky?.[0]?.dat_roz_spc ? ` · rozhodnutí ${esc(doc.pripravky[0].dat_roz_spc)}` : "";
  return `<div class="source">Zdroj: <b>SÚKL, ${esc(doc.id)}</b>${spz}${dat}</div>`;
}
/** Bod 1 může obsahovat i poznámky v závorkách nebo přetékající řádky – pro nadpis bereme jen názvy. */
function docNames(doc) {
  const parts = (doc.nazev_spc || "").split(" | ").map((x) => x.trim())
    .filter((x) => x && !x.startsWith("(") && x.length <= 90);
  return parts.length ? parts : null;
}
function docLabel(doc) {
  const n = docNames(doc);
  if (n) return n[0] + (n.length > 1 ? ` (+${n.length - 1})` : "");
  const p = doc.pripravky?.[0];
  return p ? `${p.nazev} ${p.sila || ""} ${p.forma || ""}`.trim() : doc.id;
}

// ---- home
function homeView() {
  const fav = state.user.fav.map((id) => state.byId.get(id)).filter(Boolean);
  const hist = state.user.hist.map((id) => state.byId.get(id)).filter((g) => g && !isFav(g.id)).slice(0, 15);
  let html = "";
  if (!state.groups.length) { html += `<p class="empty">Data ještě nejsou načtená.</p><p><a class="btn primary" href="#/nastaveni">Načíst data</a></p>`; }
  if (fav.length) html += `<div class="section-label">Připnuté</div>` + groupList(fav);
  if (hist.length) html += `<div class="section-label">Naposledy hledané</div>` + groupList(hist);
  if (state.groups.length && !fav.length && !hist.length) html += `<p class="empty">Začni hledáním dole – látka, obchodní název nebo ATC kód.</p>`;
  setView(html);
}
function groupList(groups, via) {
  return `<ul class="list">${groups.map((g) => {
    const bits = [esc(g.atc)];
    if (g.cesty?.[0]) bits.push(esc(g.cesty[0].toLowerCase()));
    if (g.latky?.length && norm(g.latky.join(" ")) !== norm(g.nazev)) bits.push(esc(g.latky.slice(0, 2).map(titleCase).join(", ")));
    const v = via && via.get(g.id);
    if (v && norm(v) !== norm(g.nazev)) bits.push(`<b>${esc(titleCase(v))}</b>`);
    return `<li><a href="#/g/${esc(g.id)}"><div class="row-title">${esc(titleCase(g.nazev))}</div><div class="row-sub">${bits.join(" · ")}</div></a></li>`;
  }).join("")}</ul>`;
}
function titleCase(s) { s = String(s || ""); return s === s.toUpperCase() ? s.charAt(0) + s.slice(1).toLowerCase() : s; }

function searchView(q) {
  const res = search(q);
  if (!res.length) { setView(`<p class="empty">Nic nenalezeno pro „${esc(q)}“. Zkus část názvu látky nebo ATC kód.</p>`); return; }
  const via = new Map(res.map((r) => [r.g.id, r.via]));
  setView(groupList(res.map((r) => r.g), via));
}

// ---- group
async function groupView(id) {
  const g = state.byId.get(id);
  if (!g) { setView(`<p class="empty">Skupina nenalezena.</p>`); return; }
  await pushHist(id);
  const docs = (await Promise.all(g.dokumenty.map(docGet))).filter(Boolean);
  const supplied = (d) => (d.pripravky || []).filter((p) => p.dodavky === "1").length;
  docs.sort((a, b) => supplied(b) - supplied(a) || (b.pripravky || []).length - (a.pripravky || []).length);
  const last = state.user["last_" + id];
  const chosen = docs.find((d) => d.id === last) || docs[0];
  let html = `<div class="doc-head"><h1>${esc(titleCase(g.nazev))}</h1><span class="meta">${esc(g.atc)} · ${esc((g.atc_rodice || []).slice(-1).map((r) => titleCase(r.nazev)).join(""))}</span>`;
  if (g.cesty?.length) html += `<span class="meta">${esc(g.cesty.join(", "))} · ${esc((g.formy || []).join(", "))}</span>`;
  if (g.latky?.length) html += `<span class="meta">Léčivé látky: ${esc(g.latky.map(titleCase).join(", "))}</span>`;
  html += `</div><div class="actions"><button class="btn small" id="fav">${isFav(id) ? "Odepnout" : "Připnout na úvod"}</button><a class="btn small" href="#/x?add=${esc(id)}">Do křížového odkazu</a></div>`;
  if (!docs.length) { html += `<p class="empty">${state.docsLoaded ? "Pro tuto skupinu není v datové sadě žádný text SPC." : "Texty SPC se ještě načítají – zkus to za chvíli."}</p>`; setView(html); bindFav(id); return; }
  if (docs.length > 1) {
    html += `<div class="docpicker"><div class="section-label">SPC v datové sadě (${docs.length})</div><ul class="list">` +
      docs.map((d) => {
        const sup = supplied(d);
        const forms = [...new Set((d.pripravky || []).map((p) => p.forma_nazev || p.forma).filter(Boolean))].slice(0, 2).join(", ");
        return `<li${d === chosen ? ' class="current"' : ""}><a href="#/d/${esc(d.id)}"><div class="row-title">${esc(docLabel(d))}</div><div class="row-sub">${esc(forms)} · ${(d.pripravky || []).length} balení${sup ? `, ${sup} dodávaných` : ""} · ${d.zdroj === "EMA" ? "EMA" : "SÚKL"}</div></a></li>`;
      }).join("") + `</ul></div>`;
  }
  const others = (g.pripravku || 0) - (g.pripravku_v_datech || 0);
  html += `<div class="section-label">Obchodní názvy s tímto ATC (${(g.obchodni_nazvy || []).length})</div><p class="meta">${esc((g.obchodni_nazvy || []).join(", "))}</p>`;
  if (others > 0) html += `<p class="meta">Dalších ${others} balení tohoto ATC má vlastní SPC, které v datové sadě není (rozsah: 1 SPC na ATC a lékovou formu). Text výše platí pro balení vypsaná u dokumentu, u ostatních se může lišit – ověř v SPC konkrétního přípravku.</p>`;
  setView(html); bindFav(id);
  if (docs.length === 1) location.replace(`#/d/${chosen.id}`);
}
function bindFav(id) { const b = $("#fav"); if (b) b.onclick = async () => { await toggleFav(id); b.textContent = isFav(id) ? "Odepnout" : "Připnout na úvod"; }; }

// ---- document
async function docView(id, open) {
  const doc = await docGet(id);
  if (!doc) { setView(`<p class="empty">${state.docsLoaded ? "Dokument v datové sadě není." : "Texty SPC se ještě načítají."}</p>`); return; }
  const g = findGroupForDoc(id);
  if (g) { state.user["last_" + g.id] = id; await pushHist(g.id); }
  const nazvy = [...new Set((doc.pripravky || []).map((p) => p.nazev))];
  let html = `<div class="doc-head">`;
  if (g) html += `<a href="#/g/${esc(g.id)}" class="meta">← ${esc(titleCase(g.nazev))} · ${esc(g.atc)}</a>`;
  const names = docNames(doc);
  html += `<h1>${esc(names ? names.slice(0, 3).join(" / ") + (names.length > 3 ? ` (+${names.length - 3})` : "") : docLabel(doc))}</h1></div>`;
  html += sourceStrip(doc);
  html += `<details class="sec"><summary><span class="num"></span>Balení s tímto SPC (${(doc.pripravky || []).length})</summary><div class="body"><ul class="bullets">${(doc.pripravky || []).map((p) => `<li>${esc(p.nazev)} ${esc(p.sila)} ${esc(p.forma_nazev || p.forma)} ${esc(p.baleni)} <small>(${esc(p.kod_sukl)}${p.dodavky === "1" ? ", dodáváno" : ""})</small></li>`).join("")}</ul></div></details>`;
  const a = doc.analyza_42;
  if (a && a.davky_na_hmotnost && a.davky_na_hmotnost.length) html += calcHtml(doc);
  else if (doc.sekce["4.2"]) html += `<p class="meta">Kalkulačka není k dispozici: v bodě 4.2 nebyla nalezena dávka vztažená na kg ani m².</p>`;
  html += renalPedHtml(doc);
  for (const k of SEKCE) {
    html += `<details class="sec" id="sec-${k.replace(".", "-")}"${open === k ? " open" : ""}><summary><span class="num">${k}</span>${esc(state.manifest?.meta?.sekce_nazvy?.[k] || "")}</summary><div class="body">${sourceStrip(doc).replace("Zdroj:", `Bod ${k},`)}${renderSpcText(doc.sekce[k])}</div></details>`;
  }
  setView(html);
  bindCalc(doc);
  if (open) { const el = $(`#sec-${open.replace(".", "-")}`); if (el) el.scrollIntoView(); }
}
function findGroupForDoc(id) { for (const g of state.groups) if (g.dokumenty.includes(id)) return g; return null; }

// ---- calculator (deterministic; only expressions found verbatim in section 4.2)
function calcHtml(doc) {
  const items = uniqueDoses(doc.analyza_42.davky_na_hmotnost);
  const needsBsa = items.some((d) => d.na === "m2");
  return `<div class="calc" id="calc"><h2>Výpočet dávky z textu bodu 4.2</h2>
  <p class="meta">Počítá se jen výraz nalezený v SPC: hodnota × hmotnost${needsBsa ? " (nebo × povrch těla)" : ""}. Interval a maximální dávky čti ve větě u výsledku – aplikace je nepočítá.</p>
  <div class="inputs"><label>Hmotnost (kg)<input id="kg" type="number" inputmode="decimal" min="0" step="0.1"></label>${needsBsa ? `<label>Povrch těla (m²)<input id="bsa" type="number" inputmode="decimal" min="0" step="0.01"></label>` : ""}</div>
  <div id="calc-out">${items.map((d, i) => calcItem(d, i, null, null)).join("")}</div></div>`;
}
function uniqueDoses(list) {
  const seen = new Map();
  for (const d of list) { const k = d.text + "|" + (d.veta || "").slice(0, 80); if (!seen.has(k)) seen.set(k, d); }
  return [...seen.values()];
}
function calcItem(d, i, kg, bsa) {
  const factor = d.na === "m2" ? bsa : kg;
  const per = d.na === "m2" ? "m²" : "kg";
  let result = `<span>zadej ${d.na === "m2" ? "povrch těla" : "hmotnost"}</span>`;
  if (factor > 0) {
    if (d.typ === "kombinace") {
      const u = d.jednotky || [];
      const comp = (arr) => arr.map((v, j) => `${fmtNum(v * factor)} ${esc(u[j] || "")}`).join(" / ");
      result = comp(d.slozky_od) + (d.slozky_do ? ` – ${comp(d.slozky_do)}` : "");
    } else {
      result = `${fmtNum(d.od * factor)}${d.do != null ? ` – ${fmtNum(d.do * factor)}` : ""} ${esc(d.jednotka)}`;
    }
    result += `<span> ${d.za_den ? "za den" : ""} (× ${fmtNum(factor)} ${per})</span>`;
  }
  return `<div class="calc-item"><div class="expr">${esc(d.text)}</div><div class="result">${result}</div><div class="quote">Bod 4.2: „${highlightIn(d.veta || "", d.text)}“</div></div>`;
}
function highlightIn(sentence, expr) {
  const i = sentence.indexOf(expr);
  if (i < 0) return esc(sentence);
  return esc(sentence.slice(0, i)) + "<b>" + esc(expr) + "</b>" + esc(sentence.slice(i + expr.length));
}
function bindCalc(doc) {
  const kg = $("#kg"), bsa = $("#bsa"), out = $("#calc-out");
  if (!kg || !out) return;
  const items = uniqueDoses(doc.analyza_42.davky_na_hmotnost);
  const upd = () => { out.innerHTML = items.map((d, i) => calcItem(d, i, parseFloat(String(kg.value).replace(",", ".")), bsa ? parseFloat(String(bsa.value).replace(",", ".")) : null)).join(""); };
  kg.addEventListener("input", upd); if (bsa) bsa.addEventListener("input", upd);
}

/** Úprava při poruše ledvin/jater a pediatrie: jen odstavce z bodu 4.2, které tato slova obsahují. */
function renalPedHtml(doc) {
  const t = doc.sekce["4.2"];
  if (!t) return "";
  const blocks = [
    ["Ledviny", /ledvin|renal|clearance|crcl|egfr|dialyz|hemodial/],
    ["Játra", /jater|jatern|hepat|child-pugh/],
    ["Děti", /pediatr|\bdet[ie]\b|\bdeti\b|detsk|kojenc|novorozen|dospivaj|batol/],
    ["Starší pacienti", /starsi|geriatr|senior/],
  ];
  let html = `<details class="sec"><summary><span class="num">4.2</span>Ledviny · játra · děti · senioři – co k tomu říká bod 4.2</summary><div class="body">${sourceStrip(doc).replace("Zdroj:", "Bod 4.2,")}`;
  for (const [name, re] of blocks) {
    const ps = paragraphsMatching(t, re);
    html += `<h3>${name}</h3>`;
    html += ps.length ? ps.map((p) => renderSpcText(p)).join("") : `<p class="empty">SPC v bodě 4.2 o tomto nic neuvádí (slovo se v textu bodu 4.2 nevyskytuje).</p>`;
  }
  return html + `</div></details>`;
}

// ---- cross-reference
async function xrefView(params) {
  if (params.get("add")) { const id = params.get("add"); if (!state.user.xr.includes(id)) { state.user.xr.push(id); await saveUser(); } location.replace("#/x"); return; }
  const groups = state.user.xr.map((id) => state.byId.get(id)).filter(Boolean);
  let html = `<h1>Křížový odkaz v textu SPC</h1>
  <div class="notice">Toto není interakční databáze. Zobrazí se bod 4.5 každého vybraného léku a zvýrazní se jen místa, kde se v něm objevuje název látky, přípravku nebo ATC skupiny jiného léku ze seznamu. Žádná závažnost, žádné doporučení – to musíš přečíst v textu.</div>
  <div class="xr-chosen" id="chips">${groups.map((g) => `<span class="chip">${esc(titleCase(g.nazev))}<button data-rm="${esc(g.id)}" aria-label="Odebrat">×</button></span>`).join("") || `<span class="meta">Přidej léky přes hledání dole (výsledek se zobrazí jako „Do křížového odkazu“) nebo z detailu léku.</span>`}</div>
  <label class="meta"><input type="checkbox" id="xr-more"> zobrazit i body 4.3 a 4.4</label>
  <div id="xr-out"></div>`;
  setView(html);
  $("#chips").addEventListener("click", async (e) => { const id = e.target.dataset.rm; if (id) { state.user.xr = state.user.xr.filter((x) => x !== id); await saveUser(); xrefView(new URLSearchParams()); } });
  const render = async () => {
    const more = $("#xr-more").checked;
    const out = $("#xr-out");
    if (groups.length < 2) { out.innerHTML = groups.length ? `<p class="empty">Přidej aspoň ještě jeden lék.</p>` : ""; return; }
    let h = "";
    for (const g of groups) {
      const docId = state.user["last_" + g.id] || g.dokumenty[0];
      const doc = await docGet(docId);
      const others = groups.filter((x) => x.id !== g.id);
      const hl = makeHighlighter(others);
      h += `<div class="xr-doc"><h2>${esc(titleCase(g.nazev))} <span class="meta">${esc(g.atc)}</span></h2>`;
      if (!doc) { h += `<p class="empty">Text SPC není načtený.</p></div>`; continue; }
      h += sourceStrip(doc);
      if (g.dokumenty.length > 1) h += `<p class="meta">Zobrazeno SPC: ${esc(docLabel(doc))} (<a href="#/g/${esc(g.id)}">vybrat jiné</a>)</p>`;
      for (const k of more ? ["4.3", "4.4", "4.5"] : ["4.5"]) {
        h += `<h3>${k} ${esc(state.manifest?.meta?.sekce_nazvy?.[k] || "")}</h3>` + renderSpcText(doc.sekce[k], hl);
      }
      h += `</div>`;
    }
    out.innerHTML = h;
  };
  $("#xr-more").addEventListener("change", render);
  render();
}

/** Zvýrazňovač: názvy látek, přípravků a ATC skupin ostatních léků ze seznamu, s tolerancí ke skloňování
    (porovnává se kmen slova bez diakritiky; zvýrazňuje se v původním textu). */
function makeHighlighter(groups) {
  const stems = new Set();
  const stem = (w) => (w.length >= 9 ? w.slice(0, w.length - 3) : w.length >= 7 ? w.slice(0, w.length - 2) : w.length >= 6 ? w.slice(0, w.length - 1) : w);
  for (const g of groups) {
    const names = [g.nazev, ...(g.latky || []), ...(g.obchodni_nazvy || []), ...(g.synonyma || []).filter((s) => s.length >= 5),
      ...(g.atc_rodice || []).filter((r) => r.kod.length >= 3).map((r) => r.nazev)];
    for (const raw of names) {
      for (const w of norm(raw).split(" ")) {
        if (w.length >= 5 && !STOP.has(w) && !/^\d/.test(w)) stems.add(stem(w));
      }
    }
  }
  const pats = [...stems].sort((a, b) => b.length - a.length).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "[a-z]{0,4}");
  if (!pats.length) return esc;
  const re = new RegExp("(?<![a-z0-9])(?:" + pats.join("|") + ")(?![a-z0-9])", "g");
  return (text) => {
    const f = fold(text);
    let out = "", last = 0, m;
    re.lastIndex = 0;
    while ((m = re.exec(f))) { out += esc(text.slice(last, m.index)) + "<mark>" + esc(text.slice(m.index, m.index + m[0].length)) + "</mark>"; last = m.index + m[0].length; }
    return out + esc(text.slice(last));
  };
}
const STOP = new Set(("kyselina kyseliny sodna sodny sodne natrii kalii calcii magnesii acidum jine jina jini ostatni kombinace kombinaci "
  + "lecivo leciva leciv lecive lecivych pripravky pripravek roztok tablety tableta potahovane injekcni monohydrat dihydrat trihydrat hemihydrat "
  + "hydrochlorid dihydrochlorid chlorid bromid hydrobromid sulfat fosfat citrat tartarat maleat mesilat tosylat besilat fumarat hydrogenfumarat "
  + "acetat propionat valerat sukcinat laktat glukonat karbonat nitrat oxid hydroxid natrium kalium calcium magnesium sodium potassium "
  + "systemove systemova systemovou aplikaci lecbe lecba pouziti forte rapid retard prolong junior baby active kids combi comp mite plus "
  + "pharma teva sandoz zentiva mylan viatris stada krka actavis aurovitas ratiopharm hexal glenmark medreg xantis egis polpharma "
  + "kabi braun fresenius accord olikla vipharm apotex accord-healthcare neuraxpharm").split(/\s+/));

// ---- settings / data
function settingsView() {
  const m = state.manifest;
  let html = `<h1>Data</h1>`;
  if (m) {
    html += `<dl class="kv"><dt>Platnost dat SÚKL</dt><dd>${esc(m.meta.platnost_od)} – ${esc(m.meta.platnost_do)}</dd><dt>Vygenerováno</dt><dd>${esc(m.meta.vygenerovano)}</dd><dt>DLP / SPC</dt><dd>${esc(m.meta.dlp_zip)} / ${esc(m.meta.spc_zip)}</dd><dt>Skupin ATC</dt><dd>${m.skupin}</dd><dt>Dokumentů SPC</dt><dd>${m.dokumentu}${state.docsLoaded ? "" : " (načítání nedokončeno)"}</dd><dt>Verze dat</dt><dd>${esc(m.verze)}</dd><dt>Aplikace</dt><dd>${APP_VERSION}</dd></dl>`;
  } else html += `<p class="empty">Data nejsou načtená.</p>`;
  html += `<div class="progress" id="prog" hidden><div id="prog-label" class="meta"></div><div class="bar"><i id="prog-bar"></i></div></div>
  <div class="actions"><button class="btn primary" id="load">${m ? (state.docsLoaded ? "Zkontrolovat a stáhnout nová data" : "Dokončit načítání") : "Načíst data"}</button><button class="btn" id="reload">Načíst znovu od začátku</button></div>
  <p class="meta">Data se stahují z repozitáře na GitHub Pages a ukládají do úložiště prohlížeče. iOS může úložiště webu po delší nečinnosti smazat – aplikaci přidej na plochu a data jdou kdykoli znovu načíst.</p>
  <div class="actions"><button class="btn" id="swreset">Aktualizovat aplikaci (vymazat cache)</button></div>
  <h2>Oblíbené a historie</h2><div class="actions"><button class="btn" id="exp">Exportovat do JSON</button><button class="btn" id="imp">Importovat z JSON</button></div>
  <textarea class="io" id="io" placeholder="Sem vlož JSON pro import, nebo se sem zobrazí export."></textarea>`;
  setView(html);
  const prog = $("#prog"), label = $("#prog-label"), bar = $("#prog-bar");
  const onProgress = (p) => { prog.hidden = false; label.textContent = `${p.done}/${p.total} · ${p.step}`; bar.style.width = Math.round(100 * p.done / p.total) + "%"; };
  const run = async (force) => {
    try {
      await downloadData(onProgress, { force });
      showBanner(""); updateDataStatus();
      // nepřekreslovat, pokud mezitím odešel jinam (třeba už začal hledat)
      if ((location.hash || "").startsWith("#/nastaveni")) settingsView();
    } catch (e) { showBanner("Načtení dat selhalo: " + e.message + (navigator.onLine ? "" : " (jsi offline)"), true); }
  };
  $("#load").onclick = () => run(false);
  $("#reload").onclick = () => { if (confirm("Smazat uložené texty SPC a stáhnout vše znovu?")) run(true); };
  $("#swreset").onclick = async () => { if ("serviceWorker" in navigator) { const rs = await navigator.serviceWorker.getRegistrations(); await Promise.all(rs.map((r) => r.unregister())); } if (window.caches) { const ks = await caches.keys(); await Promise.all(ks.map((k) => caches.delete(k))); } location.reload(); };
  $("#exp").onclick = () => { $("#io").value = JSON.stringify({ fav: state.user.fav, hist: state.user.hist, xr: state.user.xr, exportovano: new Date().toISOString() }, null, 1); $("#io").select(); };
  $("#imp").onclick = async () => { try { const o = JSON.parse($("#io").value); state.user.fav = o.fav || []; state.user.hist = o.hist || []; state.user.xr = o.xr || []; await saveUser(); showBanner("Import hotov."); } catch { showBanner("Import selhal – neplatný JSON.", true); } };
}

// ---------------------------------------------------------------- shell
function showBanner(msg, isErr) { const b = $("#banner"); b.hidden = !msg; b.textContent = msg; b.className = "banner" + (isErr ? " err" : ""); }
function updateDataStatus() {
  const el = $("#datastatus"); const m = state.manifest;
  if (!m) { el.textContent = "bez dat"; el.className = "datastatus stale"; return; }
  const to = parseCzDate(m.meta.platnost_do);
  const stale = to && (Date.now() - to.getTime()) / 864e5 > STALE_DAYS;
  el.textContent = `Data SÚKL do ${fmtDate(to)}`;
  el.className = "datastatus" + (stale ? " stale" : "");
  if (stale) showBanner(`Data jsou starší než 3 měsíce (platnost do ${fmtDate(to)}). Spusť ETL a nahraj nová data.`);
}

function route() {
  const h = location.hash || "#/";
  const [path, qs] = h.slice(1).split("?");
  const params = new URLSearchParams(qs || "");
  const parts = path.split("/").filter(Boolean);
  const q = $("#q");
  if (parts[0] !== "s") q.value = params.get("q") || "";
  if (!parts.length) return homeView();
  if (parts[0] === "s") { const v = decodeURIComponent(parts[1] || ""); if (q.value !== v) q.value = v; return searchView(v); }
  if (parts[0] === "g") return groupView(decodeURIComponent(parts[1]));
  if (parts[0] === "d") return docView(decodeURIComponent(parts[1]), params.get("bod"));
  if (parts[0] === "x") return xrefView(params);
  if (parts[0] === "nastaveni") return settingsView();
  homeView();
}

function bindSearch() {
  const q = $("#q");
  let t = null;
  q.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => { const v = q.value.trim(); if (v) history.replaceState(null, "", "#/s/" + encodeURIComponent(v)); else history.replaceState(null, "", "#/"); route(); }, 60); });
  $("#searchbar").addEventListener("submit", (e) => { e.preventDefault(); q.blur(); });
  $("#clear").addEventListener("click", () => { q.value = ""; location.hash = "#/"; q.focus(); });
}

async function main() {
  bindSearch();
  window.addEventListener("hashchange", route);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js").catch(() => {});
  try {
    const had = await loadFromStore();
    updateDataStatus();
    route();
    if (!had) {
      if (navigator.onLine) { location.hash = "#/nastaveni"; setTimeout(() => $("#load")?.click(), 50); }
      else showBanner("Žádná data a jsi offline. Připoj se a načti data.", true);
    } else if (!state.docsLoaded && navigator.onLine) {
      showBanner("Texty SPC nejsou celé načtené."); const b = $("#banner"); const btn = document.createElement("button"); btn.className = "btn small"; btn.textContent = "Dokončit"; btn.onclick = () => { location.hash = "#/nastaveni"; setTimeout(() => $("#load")?.click(), 50); }; b.appendChild(btn);
    } else if (navigator.onLine) {
      const upd = await checkForUpdate();
      if (upd) { showBanner(`Nová data (platnost ${upd.meta.platnost_od} – ${upd.meta.platnost_do}).`); const b = $("#banner"); const btn = document.createElement("button"); btn.className = "btn small"; btn.textContent = "Aktualizovat"; btn.onclick = () => { location.hash = "#/nastaveni"; setTimeout(() => $("#load")?.click(), 50); }; b.appendChild(btn); }
    }
  } catch (e) { showBanner("Chyba úložiště: " + e.message, true); }
}
if (IS_BROWSER) main();

// export for tests (node)
if (typeof module !== "undefined") module.exports = { fold, norm, editDistance, search, setGroups, state, renderSpcText, paragraphsMatching, makeHighlighter, uniqueDoses, fmtNum };
