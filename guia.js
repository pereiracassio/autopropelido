// Guia passo a passo: instruções de curva e posição do usuário sobre o caminho.
// Funciona no navegador (window.Guia) e no Node (module.exports), para poder testar.
(function (raiz) {
  var R = 6371000, RAD = Math.PI / 180;

  function dist(la1, lo1, la2, lo2) {
    var dLa = (la2 - la1) * RAD, dLo = (lo2 - lo1) * RAD;
    var a = Math.sin(dLa / 2) * Math.sin(dLa / 2) + Math.cos(la1 * RAD) * Math.cos(la2 * RAD) * Math.sin(dLo / 2) * Math.sin(dLo / 2);
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  function rumo(la1, lo1, la2, lo2) {
    var y = Math.sin((lo2 - lo1) * RAD) * Math.cos(la2 * RAD);
    var x = Math.cos(la1 * RAD) * Math.sin(la2 * RAD) - Math.sin(la1 * RAD) * Math.cos(la2 * RAD) * Math.cos((lo2 - lo1) * RAD);
    return (Math.atan2(y, x) / RAD + 360) % 360;
  }

  function onde(nome) {
    if (!nome || nome === 'rua sem nome') return 'na rua sem nome';
    return (/^(Rua|Avenida|Travessa|Estrada|Alameda|Praça|Rodovia|Via|Viela|Ladeira)\b/.test(nome) ? 'na ' : 'no ') + nome;
  }

  // r: resultado de Rota.caminho (pontos, segNomes). Devolve distâncias acumuladas e a lista de passos.
  function preparar(r) {
    var pts = r.pontos, nm = r.segNomes, cum = [0], i;
    for (i = 1; i < pts.length; i++) cum.push(cum[i - 1] + dist(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]));
    var passos = [{ i: 0, texto: 'Siga ' + onde(nm[0]) }];
    for (var k = 1; k < nm.length; k++) {
      if (nm[k] === nm[k - 1]) continue;
      // direção ~15 m antes e ~15 m depois da esquina
      var ib = k; while (ib > 0 && cum[k] - cum[ib] < 15) ib--;
      var ia = k; while (ia < pts.length - 1 && cum[ia] - cum[k] < 15) ia++;
      var b1 = rumo(pts[ib][0], pts[ib][1], pts[k][0], pts[k][1]);
      var b2 = rumo(pts[k][0], pts[k][1], pts[ia][0], pts[ia][1]);
      var d = ((b2 - b1 + 540) % 360) - 180, a = Math.abs(d), lado = d > 0 ? 'direita' : 'esquerda', t;
      if (a < 20) t = 'Siga em frente ' + onde(nm[k]);
      else if (a < 60) t = 'Vire ligeiramente à ' + lado + ' ' + onde(nm[k]);
      else if (a < 135) t = 'Vire à ' + lado + ' ' + onde(nm[k]);
      else t = 'Faça o retorno ' + onde(nm[k]);
      if (a < 20 && (!nm[k] || nm[k] === 'rua sem nome')) continue;
      if (cum[k] - cum[passos[passos.length - 1].i] < 25 && a < 60) continue;
      passos.push({ i: k, texto: t });
    }
    passos.push({ i: pts.length - 1, texto: 'Você chegou' });
    return { pts: pts, cum: cum, total: cum[cum.length - 1], passos: passos };
  }

  // ponto do caminho mais perto de (lat, lon), olhando só os pedacinhos de 'de' até 'ate'
  function projetar(g, lat, lon, de, ate) {
    var melhor = null, n = g.pts.length;
    var c = Math.cos(lat * RAD);
    for (var i = Math.max(0, de); i <= Math.min(n - 2, ate); i++) {
      var ax = (g.pts[i][1] - lon) * c * 111320, ay = (g.pts[i][0] - lat) * 110540;
      var bx = (g.pts[i + 1][1] - lon) * c * 111320, by = (g.pts[i + 1][0] - lat) * 110540;
      var dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
      var t = l2 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / l2)) : 0;
      var px = ax + t * dx, py = ay + t * dy, d = Math.sqrt(px * px + py * py);
      if (!melhor || d < melhor.dist) melhor = { seg: i, t: t, dist: d, lat: lat + py / 110540, lon: lon + px / (c * 111320), along: g.cum[i] + t * (g.cum[i + 1] - g.cum[i]) };
    }
    return melhor;
  }

  // próximo passo: o primeiro cuja esquina ainda não passou
  function proximo(g, seg) {
    for (var k = 0; k < g.passos.length; k++) if (g.passos[k].i > seg) return g.passos[k];
    return g.passos[g.passos.length - 1];
  }

  var API = { preparar: preparar, projetar: projetar, proximo: proximo, dist: dist };
  if (typeof module !== 'undefined' && module.exports) module.exports = API; else raiz.Guia = API;
})(typeof window !== 'undefined' ? window : this);
