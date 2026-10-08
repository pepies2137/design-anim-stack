#!/bin/sh
# Entrypoint motion-anything:
#  - config opencode (engine) z env
#  - app na 127.0.0.1:4398 (upstream binduje sie tylko na loopback)
#  - caddy na 0.0.0.0:4399 z basic auth (workbench nie ma wlasnego uwierzytelniania)
set -e

HOME_DIR="${HOME:-/home/ma}"
mkdir -p "$HOME_DIR/.config/opencode" "$HOME_DIR/.local/share/opencode" "$HOME_DIR/.cache"
mkdir -p /app/app/projects /app/app/user-skills

export OPENCODE_ENABLE_OD_MCP="${OPENCODE_ENABLE_OD_MCP:-0}"
node /opt/opencode/init-config.mjs
node /opt/opencode/init-auth.mjs

MA_PORT=4398
PUBLIC_PORT="${MOTION_PORT:-4399}"

# Caddyfile z hashem bcrypt liczonym w locie (plaintext hasla siedzi tylko w env Dokploy,
# dzieki temu w env nie ma znakow '$' ktore psuje interpolacja compose).
: "${MOTION_USER:?brak MOTION_USER}"
: "${MOTION_PASS:?brak MOTION_PASS}"
HASH="$(caddy hash-password --plaintext "$MOTION_PASS")"
cat > /etc/caddy/Caddyfile <<EOF
:${PUBLIC_PORT} {
	basic_auth {
		${MOTION_USER} ${HASH}
	}
	reverse_proxy 127.0.0.1:${MA_PORT} {
		flush_interval -1
	}
	encode gzip
	log {
		output stdout
		format console
	}
}
EOF

echo "[design-anim] motion-anything: v$(node -e "console.log(require('/app/cli/package.json').version)" 2>/dev/null || echo '?')"
echo "[design-anim] opencode: $(opencode --version 2>/dev/null || echo BRAK)"
echo "[design-anim] model:    ${OPENCODE_MODEL:-pepies/programowanieciezkie}"
echo "[design-anim] UI:       http://0.0.0.0:${PUBLIC_PORT} (basic auth: ${MOTION_USER})"

node /app/cli/bin/motion.js serve "$MA_PORT" >/var/log/motion.log 2>&1 &
MA_PID=$!
trap 'kill $MA_PID 2>/dev/null || true' TERM INT

# czekamy az app wstanie, potem oddajemy terminal caddy'emu
for i in $(seq 1 40); do
  if node -e "fetch('http://127.0.0.1:${MA_PORT}/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" 2>/dev/null; then
    echo "[design-anim] motion-anything zyje na 127.0.0.1:${MA_PORT}"
    break
  fi
  sleep 0.5
done

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
