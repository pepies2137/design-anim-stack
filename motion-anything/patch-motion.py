#!/usr/bin/env python3
"""Patcher motion-anything (upstream nexu-io/motion-anything) na potrzeby naszego deployu.

Powod (incydent 2026-10-08): w kontenerze bez Claude Code workbench domyslnie wybieral silnik
`claude`; spawn konczyl sie ENOENT, a sciezka bledu w upstreamie wolala sendJson drugi raz
-> `ERR_HTTP_HEADERS_SENT` -> NIEUCHWYCONY wyjatek -> caly serwer motion-anything padal,
a caddy zwracal 502 na wszystko. Naprawiamy trzy rzeczy:

1. sendJson: jesli naglowki juz poszly, nie probuj pisac drugi raz (koniec z zabijaniem procesu).
2. Silnik: jesli zadany silnik nie jest zainstalowany, uzyj pierwszego zainstalowanego
   (u nas: opencode) zamiast wywalac sie na ENOENT.
3. Log w konsoli, ze podmiana nastapila — zeby bylo widac w logach deployu.

Uruchamiane w Dockerfile po `git clone`. Idempotentne.
"""
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "/app/cli/bin/motion.js"
src = open(path, encoding="utf-8").read()

if "design-anim patch" in src:
    print("patch: juz nalozony, pomijam")
    sys.exit(0)

changed = []

# --- 1. sendJson: guard na headersSent -------------------------------------
old_send = "function sendJson(res, code, obj) { res.writeHead("
new_send = "function sendJson(res, code, obj) { /* design-anim patch */ if (res.headersSent) return; res.writeHead("
if old_send in src:
    src = src.replace(old_send, new_send, 1)
    changed.append("sendJson(headersSent)")

# --- 2. helpery: czy silnik zainstalowany / pierwszy zainstalowany ----------
helpers = """  /* design-anim patch: wybor silnika odporny na brak binarki (np. brak claude w kontenerze) */
  function engineInstalled(id) {
    var d = engineDef(id);
    if (!d) return false;
    if (d.mode === 'byok') { try { return !!readByokConfig().key; } catch (e) { return false; } }
    var c = d.bins || [d.id];
    for (var i = 0; i < c.length; i++) { if (whichBin(c[i])) return true; }
    return false;
  }
  function firstInstalledCli() {
    for (var i = 0; i < KNOWN_CLIS.length; i++) {
      var id = KNOWN_CLIS[i].id;
      if (id !== 'byok' && engineInstalled(id)) return id;
    }
    return '';
  }
  function readBody(req, cb) {"""
old_read = "  function readBody(req, cb) {"
if old_read in src:
    src = src.replace(old_read, helpers, 1)
    changed.append("helpery engineInstalled/firstInstalledCli")

# --- 3. readBody: podmiana nieistniejacego silnika na pierwszy dostepny -----
old_body = "req.on('end', function () { try { cb(null, b ? JSON.parse(b) : {}); } catch (e) { cb(e); } }); }"
new_body = ("req.on('end', function () { try { var j = b ? JSON.parse(b) : {}; "
            "/* design-anim patch */ if (j && j.cli && !engineInstalled(j.cli)) { var alt = firstInstalledCli(); "
            "if (alt) { console.log('  ! silnik ' + j.cli + ' niezainstalowany -> uzywam ' + alt); j.cli = alt; } } "
            "cb(null, j); } catch (e) { cb(e); } }); }")
if old_body in src:
    src = src.replace(old_body, new_body, 1)
    changed.append("readBody(fallback silnika)")

open(path, "w", encoding="utf-8").write(src)
print("patch: nalozono ->", ", ".join(changed) or "NIC (wzorce nie pasuja — sprawdz wersje upstreamu)")
sys.exit(0 if len(changed) == 3 else 1)
