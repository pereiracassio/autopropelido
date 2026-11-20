// Caminho pelas vias permitidas: grafo montado a partir do vias.json, A* para achar o trajeto.
// Funciona no navegador (window.Rota) e no Node (module.exports), para poder testar.
(function (raiz) {
  var CELULA = 0.002; // graus (~220 m) para achar a via mais perto de um ponto

  function haversine(lat1, lon1, lat2, lon2) {
    var R = 6371000, r = Math.PI / 180;
    var dLat = (lat2 - lat1) * r, dLon = (lon2 - lon1) * r;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  // 1 = só no sentido do desenho, -1 = só no sentido contrário, 0 = os dois
  function sentido(t) {
    var o = t.oneway;
    if (o === 'yes' || o === '1' || o === 'true') return 1;
    if (o === '-1' || o === 'reverse') return -1;
    if (t.junction === 'roundabout' && !o) return 1;
    return 0;
  }

  // piso: 'pedra' (paralelepípedo e blocos), 'terra' (terra, cascalho, areia) ou 'ok'
  function pisoDe(t) {
    var s = t.surface || '';
    if (/^(paving_stones|cobblestone|sett|unhewn_cobblestone)/.test(s)) return 'pedra';
    if (/^(unpaved|dirt|ground|gravel|fine_gravel|sand|grass|earth|mud|compacted|grass_paver)$/.test(s)) return 'terra';
    return 'ok';
  }

  // vias: [{ g: [[lat,lon],...], t: tags, c: { tipo } }]
  // tipos que entram: ciclovia, ciclofaixa, via40, incerta (esta só se permitida na busca)
  function construir(vias) {
    var ids = new Map(), lat = [], lon = [], adj = [];
    function no(p) {
      var k = p[0] + ',' + p[1];
      var i = ids.get(k);
      if (i === undefined) { i = lat.length; ids.set(k, i); lat.push(p[0]); lon.push(p[1]); adj.push([]); }
      return i;
    }
    var nomes = [], pisos = [];
    vias.forEach(function (v) {
      var tipo = v.c.tipo, proib = tipo === 'nao';
      var peso = tipo === 'ciclovia' ? 0.85 : tipo === 'ciclofaixa' ? 0.95 : tipo === 'incerta' ? 1.4 : proib ? 6 : 1;
      var inc = tipo === 'incerta';
      var s = sentido(v.t);
      var wi = nomes.length; nomes.push(v.t.name || '');
      var piso = pisoDe(v.t); pisos.push(piso);
      var pm = piso === 'pedra' ? 1.5 : piso === 'terra' ? 2.2 : 1;
      peso *= pm;
      for (var k = 0; k + 1 < v.g.length; k++) {
        var a = no(v.g[k]), b = no(v.g[k + 1]);
        if (a === b) continue;
        var d = haversine(lat[a], lon[a], lat[b], lon[b]);
        if (s >= 0) adj[a].push({ to: b, d: d, w: d * peso, via: wi, inc: inc, tp: tipo, pm: pm, pr: proib });
        if (s <= 0) adj[b].push({ to: a, d: d, w: d * peso, via: wi, inc: inc, tp: tipo, pm: pm, pr: proib });
      }
    });
    // maior pedaço conectado (ignorando o sentido), para não ligar o ponto a uma ruazinha isolada
    var pai = new Int32Array(lat.length);
    for (var i = 0; i < pai.length; i++) pai[i] = i;
    function raizDe(x) { while (pai[x] !== x) { pai[x] = pai[pai[x]]; x = pai[x]; } return x; }
    adj.forEach(function (lista, a) { lista.forEach(function (e) { var ra = raizDe(a), rb = raizDe(e.to); if (ra !== rb) pai[ra] = rb; }); });
    var tam = new Map();
    for (var j = 0; j < pai.length; j++) { var r = raizDe(j); tam.set(r, (tam.get(r) || 0) + 1); }
    var maior = -1, maiorTam = 0;
    tam.forEach(function (n, r) { if (n > maiorTam) { maiorTam = n; maior = r; } });
    var principal = new Uint8Array(lat.length);
    for (var m = 0; m < pai.length; m++) if (raizDe(m) === maior) principal[m] = 1;
    var livre = new Uint8Array(lat.length);
    adj.forEach(function (lista, a) { for (var q = 0; q < lista.length; q++) if (!lista[q].pr) { livre[a] = 1; livre[lista[q].to] = 1; } });
    // grade para achar o nó mais perto
    var grade = new Map();
    for (var n = 0; n < lat.length; n++) {
      if (!principal[n]) continue;
      var key = Math.floor(lat[n] / CELULA) + ',' + Math.floor(lon[n] / CELULA);
      var c = grade.get(key); if (c) c.push(n); else grade.set(key, [n]);
    }
    return { lat: lat, lon: lon, adj: adj, nomes: nomes, pisos: pisos, grade: grade, livre: livre };
  }

  // nó permitido mais perto de um ponto (até maxM metros); null se não houver
  function maisPerto(G, plat, plon, maxM, soLivres) {
    var ci = Math.floor(plat / CELULA), cj = Math.floor(plon / CELULA);
    var melhor = null, md = Infinity;
    var anel = Math.ceil(maxM / 200) + 1;
    for (var di = -anel; di <= anel; di++) for (var dj = -anel; dj <= anel; dj++) {
      var c = G.grade.get((ci + di) + ',' + (cj + dj));
      if (!c) continue;
      for (var k = 0; k < c.length; k++) {
        if (soLivres && !G.livre[c[k]]) continue;
        var d = haversine(plat, plon, G.lat[c[k]], G.lon[c[k]]);
        if (d < md) { md = d; melhor = c[k]; }
      }
    }
    return md <= maxM ? { no: melhor, dist: md } : null;
  }

  // heap binário mínimo de [prioridade, nó]
  function Heap() { this.a = []; }
  Heap.prototype.push = function (p, n) {
    var a = this.a, i = a.length; a.push([p, n]);
    while (i > 0) { var up = (i - 1) >> 1; if (a[up][0] <= a[i][0]) break; var t = a[up]; a[up] = a[i]; a[i] = t; i = up; }
  };
  Heap.prototype.pop = function () {
    var a = this.a, top = a[0], last = a.pop();
    if (a.length) {
      a[0] = last; var i = 0;
      for (;;) {
        var l = 2 * i + 1, r = l + 1, m = i;
        if (l < a.length && a[l][0] < a[m][0]) m = l;
        if (r < a.length && a[r][0] < a[m][0]) m = r;
        if (m === i) break;
        var t = a[m]; a[m] = a[i]; a[i] = t; i = m;
      }
    }
    return top;
  };

  // A*. permitirIncerta: usa também os trechos sem velocidade marcada
  // modo: 'padrao' (equilibrado), 'curta' (só a distância) ou 'ciclo' (prefere ciclovia e ciclofaixa)
  var CICLO = { ciclovia: 0.45, ciclofaixa: 0.65, via40: 1.1, incerta: 1.6 };
  function pesoDe(e, modo) {
    var f = e.pr ? 6 : 1;
    if (modo === 'curta') return e.d * f;
    if (modo === 'ciclo') return e.d * (CICLO[e.tp] || 1) * e.pm * f;
    return e.w;
  }

  function caminho(G, de, para, permitirIncerta, modo, permitirProibido) {
    var N = G.lat.length;
    var g = new Float64Array(N).fill(Infinity), antes = new Int32Array(N).fill(-1), viaAntes = new Int32Array(N).fill(-1), fechado = new Uint8Array(N);
    var h = new Heap();
    g[de] = 0; var HF = modo === 'ciclo' ? 0.45 : modo === 'curta' ? 1 : 0.85;
    h.push(haversine(G.lat[de], G.lon[de], G.lat[para], G.lon[para]) * HF, de);
    while (h.a.length) {
      var u = h.pop()[1];
      if (fechado[u]) continue;
      fechado[u] = 1;
      if (u === para) break;
      var lista = G.adj[u];
      for (var i = 0; i < lista.length; i++) {
        var e = lista[i];
        if (e.inc && !permitirIncerta) continue;
        if (e.pr && !permitirProibido) continue;
        var ng = g[u] + pesoDe(e, modo);
        if (ng < g[e.to]) {
          g[e.to] = ng; antes[e.to] = u; viaAntes[e.to] = e.via;
          h.push(ng + haversine(G.lat[e.to], G.lon[e.to], G.lat[para], G.lon[para]) * HF, e.to);
        }
      }
    }
    if (!fechado[para]) return null;
    var nos = [], vias = [];
    for (var x = para; x !== -1; x = antes[x]) { nos.push(x); vias.push(viaAntes[x]); }
    nos.reverse(); vias.reverse();
    var pts = nos.map(function (n) { return [G.lat[n], G.lon[n]]; });
    // distância total e trechos por nome de rua
    var total = 0, trechos = [], inc = false, segNomes = [], segProib = [], proibido = 0, pedra = 0, terra = 0;
    for (var k = 1; k < nos.length; k++) {
      var a = nos[k - 1], b = nos[k], d = haversine(G.lat[a], G.lon[a], G.lat[b], G.lon[b]);
      total += d;
      var nome = G.nomes[vias[k]] || 'rua sem nome';
      segNomes.push(nome);
      if (G.pisos[vias[k]] === 'pedra') pedra += d; else if (G.pisos[vias[k]] === 'terra') terra += d;
      var ult = trechos[trechos.length - 1];
      if (ult && ult.nome === nome) ult.metros += d; else trechos.push({ nome: nome, metros: d });
      var arestas = G.adj[a], ed = null;
      for (var q = 0; q < arestas.length; q++) if (arestas[q].to === b && arestas[q].via === vias[k]) { ed = arestas[q]; break; }
      if (ed && ed.inc) inc = true;
      if (ed && ed.pr) { proibido += d; segProib.push(true); } else segProib.push(false);
    }
    return { pontos: pts, metros: total, trechos: trechos, temIncerta: inc, segNomes: segNomes, pedra: pedra, terra: terra, proibido: proibido, segProib: segProib };
  }

  // distâncias (m) de 'de' a tudo que dá para alcançar só por vias permitidas (Infinity = não alcança)
  function alcancaveis(G, de) {
    var N = G.lat.length, g = new Float64Array(N).fill(Infinity), fechado = new Uint8Array(N), h = new Heap();
    g[de] = 0; h.push(0, de);
    while (h.a.length) {
      var u = h.pop()[1];
      if (fechado[u]) continue;
      fechado[u] = 1;
      var lista = G.adj[u];
      for (var i = 0; i < lista.length; i++) {
        var e = lista[i];
        if (e.pr) continue;
        var ng = g[u] + e.d;
        if (ng < g[e.to]) { g[e.to] = ng; h.push(ng, e.to); }
      }
    }
    return g;
  }

  var API = { alcancaveis: alcancaveis, pisoDe: pisoDe, construir: construir, maisPerto: maisPerto, caminho: caminho, haversine: haversine };
  if (typeof module !== 'undefined' && module.exports) module.exports = API; else raiz.Rota = API;
})(typeof window !== 'undefined' ? window : this);
