#!/usr/bin/env bash
# Smoke test stacku design-anim. Uzycie:
#   OD_TOKEN=$(cred --raw design-anim/od_api_token) MA_USER=... MA_PASS=... bash scripts/verify.sh [host]
set -uo pipefail
HOST="${1:-127.0.0.1}"
OD_PORT="${OD_PORT:-7456}"
MA_PORT="${MA_PORT:-4399}"
: "${OD_TOKEN:?ustaw OD_TOKEN (cred --raw design-anim/od_api_token)}"
: "${MA_USER:=motion}"
: "${MA_PASS:?ustaw MA_PASS (cred --raw design-anim/ma_pass)}"
pass=0; fail=0
ok(){ echo "  [OK]   $*"; pass=$((pass+1)); }
bad(){ echo "  [FAIL] $*"; fail=$((fail+1)); }

echo "== OpenDesign (http://$HOST:$OD_PORT) =="
code=$(curl -s -o /tmp/od_health -w '%{http_code}' -m 15 "http://$HOST:$OD_PORT/api/health")
[ "$code" = "200" ] && ok "health: $code $(head -c 80 /tmp/od_health)" || bad "health: $code"
code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "http://$HOST:$OD_PORT/")
[ "$code" = "401" ] && ok "bez tokenu = 401 (auth dziala)" || bad "bez tokenu: $code (oczekiwane 401)"
code=$(curl -s -o /tmp/od_ui -w '%{http_code}' -m 15 -u "open-design:$OD_TOKEN" "http://$HOST:$OD_PORT/")
[ "$code" = "200" ] && ok "z tokenem = 200 ($(wc -c < /tmp/od_ui) B HTML)" || bad "z tokenem: $code"
grep -qi "opendesign\|open-design" /tmp/od_ui 2>/dev/null && ok "UI zawiera marker OpenDesign" || bad "brak markera OpenDesign w HTML"

echo "== motion-anything (http://$HOST:$MA_PORT) =="
code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "http://$HOST:$MA_PORT/")
[ "$code" = "401" ] && ok "bez hasla = 401 (basic auth dziala)" || bad "bez hasla: $code (oczekiwane 401)"
code=$(curl -s -o /tmp/ma_ui -w '%{http_code}' -m 15 -u "$MA_USER:$MA_PASS" "http://$HOST:$MA_PORT/")
[ "$code" = "200" ] && ok "z haslem = 200 ($(wc -c < /tmp/ma_ui) B HTML)" || bad "z haslem: $code"
grep -qi "motion" /tmp/ma_ui 2>/dev/null && ok "UI zawiera marker motion" || bad "brak markera motion w HTML"
code=$(curl -s -o /tmp/ma_api -w '%{http_code}' -m 20 -u "$MA_USER:$MA_PASS" "http://$HOST:$MA_PORT/api/engines")
if [ "$code" = "200" ]; then
  grep -q '"id":"opencode"' /tmp/ma_api && ok "engine opencode wykryty przez workbench" || bad "opencode NIE wykryty: $(head -c 200 /tmp/ma_api)"
else
  echo "  [INFO] /api/engines -> $code (sprawdz recznie w UI)"
fi

echo; echo "===== PASS=$pass FAIL=$fail ====="
[ "$fail" -eq 0 ] || exit 1
