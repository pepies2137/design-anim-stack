#!/bin/sh
# Entrypoint OpenDesign (Docker) — przygotowuje config opencode (engine) i startuje daemon.
# Baza: ghcr.io/nexu-io/od:latest (Alpine, user open-design uid 1001, ENTRYPOINT /sbin/tini --).
set -e

HOME_DIR="${HOME:-/home/open-design}"
mkdir -p "$HOME_DIR/.config/opencode" "$HOME_DIR/.local/share/opencode" "$HOME_DIR/.cache"

# 1. config opencode: templatka + placeholdery z env (OPENCODE_MODEL, OPENCODE_PEPIES_BASE_URL)
#    + wpis MCP "open-design" -> lokalny daemon (tylko tutaj: w tym kontenerze jest od + daemon)
export OPENCODE_ENABLE_OD_MCP="${OPENCODE_ENABLE_OD_MCP:-1}"
export OPENCODE_OD_DAEMON_URL="${OPENCODE_OD_DAEMON_URL:-http://127.0.0.1:${OD_PORT:-7456}}"
node /opt/opencode/init-config.mjs

# 2. auth.json opencode: klucze dostawców z env (nie trzymamy ich w obrazie ani w repo)
node /opt/opencode/init-auth.mjs

# 3. diagnoza (do logów deployu Dokploy)
echo "[design-anim] opencode: $(opencode --version 2>/dev/null || echo BRAK)"
echo "[design-anim] od cli:    $(od --help >/dev/null 2>&1 && echo ok || echo BRAK)"
echo "[design-anim] model:     ${OPENCODE_MODEL:-pepies/programowanieciezkie}"

exec node /app/apps/daemon/dist/cli.js --no-open
