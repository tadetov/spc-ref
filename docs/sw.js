/* Service worker: cache-first pro shell aplikace. Data (data/*.gz, manifest.json) se do cache nedávají – jdou do IndexedDB. */
const VERSION = "spcref-shell-v3";
const SHELL = ["./", "./index.html", "./app.js", "./style.css", "./manifest.webmanifest", "./icon.svg", "./icon-180.png"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.includes("/data/")) return; // data vždy ze sítě (a pak IndexedDB)
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then((hit) => hit || fetch(e.request).then((r) => { const copy = r.clone(); caches.open(VERSION).then((c) => c.put(e.request, copy)); return r; })));
});
