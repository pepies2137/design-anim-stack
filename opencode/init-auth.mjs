// init-auth.mjs — zapisuje klucze dostawcow do ~/.local/share/opencode/auth.json.
// Klucze WYLACZNIE z env (Dokploy -> Environment); nic nie jest wpisane w obraz ani repo.
// Format zgodny z opencode: { "<provider>": { "type": "api", "key": "<klucz>" } }
import { writeFileSync, mkdirSync, existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const home = process.env.HOME || '/root';
const dir = join(home, '.local', 'share', 'opencode');
const path = join(dir, 'auth.json');

const providers = {
  pepies: process.env.OPENCODE_PEPIES_KEY || process.env.HERMES_CUSTOM_ROUTER_PEPIES_PL_API_KEY,
  'opencode-go': process.env.OPENCODE_GO_KEY || process.env.OPENCODE_GO_API_KEY,
};

let auth = {};
if (existsSync(path)) {
  try { auth = JSON.parse(readFileSync(path, 'utf8')); } catch { auth = {}; }
}

let added = [];
for (const [name, key] of Object.entries(providers)) {
  if (key && key.trim()) { auth[name] = { type: 'api', key: key.trim() }; added.push(name); }
}

mkdirSync(dir, { recursive: true });
writeFileSync(path, JSON.stringify(auth, null, 2) + '\n');
console.log('[design-anim] auth.json ->', path, '| dostawcy z env:', added.join(', ') || 'brak (sprawdz env!)', '| w pliku:', Object.keys(auth).join(', '));
