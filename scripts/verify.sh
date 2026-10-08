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
code=$(curl -s -o /tmp/od_agents -w '%{http_code}' -m 30 -u "open-design:$OD_TOKEN" "http://$HOST:$OD_PORT/api/agents")
if [ "$code" = "200" ]; then
  python3 -c "
import json,sys
d=json.load(open('/tmp/od_agents'))
oc=[a for a in d.get('agents',[]) if a.get('id')=='opencode']
sys.exit(0 if oc and oc[0].get('available') else 1)
" && ok "OpenDesign widzi silnik opencode (/api/agents: available)" || bad "OpenDesign NIE widzi opencode: $(head -c 200 /tmp/od_agents)"
else
  bad "/api/agents -> $code"
fi

echo "== motion-anything (http://$HOST:$MA_PORT) =="
code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "http://$HOST:$MA_PORT/")
[ "$code" = "401" ] && ok "bez hasla = 401 (basic auth dziala)" || bad "bez hasla: $code (oczekiwane 401)"
code=$(curl -s -o /tmp/ma_ui -w '%{http_code}' -m 15 -u "$MA_USER:$MA_PASS" "http://$HOST:$MA_PORT/")
[ "$code" = "200" ] && ok "z haslem = 200 ($(wc -c < /tmp/ma_ui) B HTML)" || bad "z haslem: $code"
grep -qi "motion" /tmp/ma_ui 2>/dev/null && ok "UI zawiera marker motion" || bad "brak markera motion w HTML"
code=$(curl -s -o /tmp/ma_clis -w '%{http_code}' -m 30 -u "$MA_USER:$MA_PASS" "http://$HOST:$MA_PORT/api/clis")
if [ "$code" = "200" ]; then
  if grep -q '"id":"opencode","name":"OpenCode","vendor":"OpenCode","installed":true' /tmp/ma_clis || python3 -c "
import json,sys
d=json.load(open('/tmp/ma_clis'))
sys.exit(0 if any(c.get('id')=='opencode' and c.get('installed') for c in d.get('clis',[])) else 1)
"; then
    ok "silnik opencode wykryty przez workbench (/api/clis)"
  else
    bad "opencode NIE wykryty: $(head -c 200 /tmp/ma_clis)"
  fi
else
  bad "/api/clis -> $code"
fi

code=$(curl -s -o /tmp/ma_skills -w '%{http_code}' -m 30 -u "$MA_USER:$MA_PASS" "http://$HOST:$MA_PORT/api/skills")
[ "$code" = "200" ] && ok "biblioteka przepisow: $(python3 -c "import json;print(len(json.load(open('/tmp/ma_skills')).get('skills',[])))") pozycji" || bad "/api/skills -> $code"

echo; echo "===== PASS=$pass FAIL=$fail ====="
[ "$fail" -eq 0 ] || exit 1
