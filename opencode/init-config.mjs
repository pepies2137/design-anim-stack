// init-config.mjs — buduje ~/.config/opencode/opencode.jsonc z templatki + env.
// Uzywane w OBU kontenerach (open-design, motion-anything).
// Wejscie:  /opt/opencode/opencode.template.json (bez sekretow)
// Wyjscie:  $HOME/.config/opencode/opencode.jsonc
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const home = process.env.HOME || '/root';
const out = join(home, '.config', 'opencode', 'opencode.jsonc');
const tplPath = process.env.OPENCODE_TEMPLATE || '/opt/opencode/opencode.template.json';

const tpl = readFileSync(tplPath, 'utf8');
const cfg = JSON.parse(tpl);

cfg.model = process.env.OPENCODE_MODEL || cfg.model || 'pepies/programowanieciezkie';

// baseURL dostawcy OmniRoute (pepies) — podmienialny bez przebudowy obrazu
const base = process.env.OPENCODE_PEPIES_BASE_URL;
if (base && cfg.provider?.pepies?.options) cfg.provider.pepies.options.baseURL = base;

// MCP: OpenDesign jako narzedzie dla opencode (tylko tam, gdzie stoi daemon OD)
if (process.env.OPENCODE_ENABLE_OD_MCP === '1') {
  cfg.mcp = cfg.mcp || {};
  cfg.mcp['open-design'] = {
    type: 'local',
    command: ['od', 'mcp', '--daemon-url', process.env.OPENCODE_OD_DAEMON_URL || 'http://127.0.0.1:7456'],
    enabled: true,
  };
}

mkdirSync(join(home, '.config', 'opencode'), { recursive: true });
writeFileSync(out, JSON.stringify(cfg, null, 2) + '\n');
console.log('[design-anim] config opencode ->', out, '| mcp open-design:', Boolean(cfg.mcp?.['open-design']));
