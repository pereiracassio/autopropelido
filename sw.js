// Deixa o mapa abrir na hora e funcionar mesmo sem internet (as ruas ficam guardadas no aparelho).
var VERSAO = 'autoprop-v3';
var TILES = 'autoprop-tiles-v1';
var BASE = [
  './', 'index.html', 'rota.js?v=1', 'vias.json?v=2', 'lugares.json?v=1', 'manifest.webmanifest',
  'icone-32.png?v=2', 'icone-48.png?v=2', 'icone-192.png?v=2', 'icone-512.png', 'apple-touch-icon.png',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'
];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(VERSAO).then(function (c) {
    return Promise.all(BASE.map(function (u) { return c.add(u).catch(function () {}); }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== VERSAO && k !== TILES; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function limitar(nome, max) {
  return caches.open(nome).then(function (c) {
    return c.keys().then(function (ks) { if (ks.length > max) return c.delete(ks[0]).then(function () { return limitar(nome, max); }); });
  });
}

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var u = new URL(req.url);
  // pedaços do mapa: usa o que já viu e guarda os novos (até 400)
  if (u.hostname.indexOf('tile.openstreetmap.org') >= 0) {
    e.respondWith(caches.open(TILES).then(function (c) {
      return c.match(req).then(function (hit) {
        return hit || fetch(req).then(function (r) { if (r.ok) { c.put(req, r.clone()); limitar(TILES, 400); } return r; });
      });
    }));
    return;
  }
  // o resto do site: mostra o guardado e atualiza por trás (na próxima abertura já vem o novo)
  if (u.origin === location.origin || u.hostname === 'cdnjs.cloudflare.com') {
    e.respondWith(caches.open(VERSAO).then(function (c) {
      return c.match(req, { ignoreSearch: false }).then(function (hit) {
        var rede = fetch(req).then(function (r) { if (r.ok) c.put(req, r.clone()); return r; }).catch(function () { return hit; });
        return hit || rede;
      });
    }));
  }
});
