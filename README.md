# Design & Motion Stack

Dwa narzędzia designu/animacji od [nexu.io](https://github.com/nexu-io) odpalone u nas (Dokploy, compose)
i spięte **jednym silnikiem: `opencode` CLI** (combo OmniRoute `pepies/programowanieciezkie`).

| | OpenDesign | motion-anything |
|---|---|---|
| Co to | workspace design-agenta: design systemy, prototypy, landing page, dashboardy, slajdy, eksport HTML/PDF/PPTX/MP4 | agentic motion layer: 403 przepisy ruchu, workbench, eksport JSON/CSS/React/Lottie/MP4/GIF |
| Upstream | `nexu-io/open-design` (Apache-2.0) | `nexu-io/motion-anything` (Apache-2.0) |
| Obraz | `ghcr.io/nexu-io/od:latest` + opencode | build z repo (Node 22 + opencode + caddy) |
| Port | 7456 | 4399 (UI za caddy + basic auth) |
| Auth | HTTP Basic: user `open-design`, haslo = `OD_API_TOKEN` | basic auth: `MOTION_USER` / `MOTION_PASS` |
| Dane | `/app/.od` (wolumen `od_data`) | `/app/app/projects`, `/app/app/user-skills` |

## Dlaczego to ma sens (i gdzie się to wpina)

Pętla z README upstreamu: **wybierz design system (OD) → wygeneruj stronę/ekran → nadaj ruch per komponent
(motion-anything) → wyeksportuj wynik jako `SKILL.md`** i wrzuć do repo projektu. Dla nas:

- **`app.samochodziarze.com`** i **STOLICK** — tokeny/design system raz zdefiniowane w OD, ruch z przepisów
  MA (GSAP/Lenis) zamiast wymyślania easingów od zera. Warstwa ruchu wchodzi jako `src/motion/` per
  skill `motion-layer-integration` (u nas w bibliotece skilli).
- **BOXY** — ekrany POS/kasjerki i materiały sprzedażowe: OD robi warianty layoutu, MA dodaje mikro-animacje
  feedbacku (te akurat są w kategorii „feedback & delight").
- **Eksport do mediów** — MP4/GIF bez watermarku, lokalnie (WebCodecs w przeglądarce), czyli bez płacenia
  i bez wysyłania materiałów na cudzy serwer.
- **Agent-native** — oba narzędzia są sterowane CLI/agentem, więc `opencode run` (nasza zasada: kod tylko
  przez opencode) jest jednocześnie silnikiem generowania w OD i w MA. Nie ma tu drugiego stacku AI do
  utrzymywania.

Kiedy to *nie* ma sensu: jeśli potrzebujesz wyłącznie statycznego, produkcyjnego UI w naszym istniejącym
design systemie, to OD/MA są nadmiarem — wtedy wystarczy skill `stitch-design-taste` + `motion-layer-integration`.
Traktuj ten stack jako **generator i źródło przepisów**, nie jako runtime produkcyjny naszych stron.

## Architektura

```
przeglądarka ──(basic auth)──► caddy :4399 ──► motion-anything :4398 ─┐
                                                                      ├─► spawn: opencode run --format json
przeglądarka ──(basic auth)──► OpenDesign daemon :7456 ───────────────┘         (model: pepies/programowanieciezkie,
                (od mcp = MCP do tooli OD dla opencode)                          klucz z env → auth.json)
```

- `opencode` instalowany z npm (`opencode-ai@1.18.34`), config i klucze wstrzykiwane przy starcie z env
  (`opencode/init-config.mjs`, `opencode/init-auth.mjs`). **Nic nie jest wbudowane w obrazy** — rotacja klucza
  to zmiana env + redeploy.
- motion-anything binduje się tylko na `127.0.0.1` (tak jest w upstreamie), dlatego w tym samym kontenerze stoi
  caddy: wystawia `0.0.0.0:4399` i dokłada basic auth (workbench nie ma własnego uwierzytelniania).
- `od` w obrazie OpenDesign to busybox `od` — robimy shim `/usr/local/bin/od` → `node /app/apps/daemon/dist/cli.js`,
  dzięki czemu działa `od mcp --daemon-url http://127.0.0.1:7456` (i stąd MCP `open-design` w configu opencode).

## Uruchomienie

### Lokalnie (docker compose, bez Dokploy)

```bash
cp .env.example .env      # wpisz sekrety: cred --raw design-anim/od_api_token, cred --raw design-anim/ma_pass, klucze OmniRoute
docker compose up -d --build
OD_TOKEN=$(cred --raw design-anim/od_api_token) MA_PASS=$(cred --raw design-anim/ma_pass) bash scripts/verify.sh
```

### W Dokploy

Projekt: **Design & Motion** (`design-anim`), compose z tego repo (`sourceType: git`, `composePath: docker-compose.yml`).
Zmienne środowiskowe wklejone z `.env.example` (wartości w vaulcie). Po zmianie env: **Redeploy**.

```bash
KEY=$(cred --raw m75q/dokploy_api_key)
# utworzenie compose (jednorazowo)
curl -sS -X POST http://localhost:3000/api/compose.create -H "x-api-key: $KEY" -H 'Content-Type: application/json' \
  -d '{"name":"design-anim","environmentId":"<ENV_ID>","sourceType":"git",
       "customGitUrl":"https://github.com/pepies2137/design-anim-stack.git","customGitBranch":"main",
       "composePath":"docker-compose.yml","composeType":"docker-compose"}'
# env + deploy
curl -sS -X POST http://localhost:3000/api/compose.update -H "x-api-key: $KEY" -H 'Content-Type: application/json' \
  -d "{\"composeId\":\"<COMPOSE_ID>\",\"env\":\"$(python3 -c 'print(open(".env").read())' | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')\"}"
curl -sS -X POST http://localhost:3000/api/compose.deploy -H "x-api-key: $KEY" -H 'Content-Type: application/json' \
  -d '{"composeId":"<COMPOSE_ID>"}'
```

## Publiczne domeny (opcjonalnie)

Box stoi za CGNAT, więc wejście z internetu wymaga Cloudflare Tunnel (tak jak `stolick.pl`).
Wzór: nowy tunnel `design-anim` → ingress `design.<domena>` → `http://<host-ip>:7456` (OD) oraz
`motion.<domena>` → `http://<host-ip>:4399` (MA, basic auth zostaje na caddy).
Do tego `OD_ALLOWED_ORIGINS=https://design.<domena>` w env.

## Integracja z agentami

- **opencode (w kontenerze OD)**: `mcp.open-design` = `od mcp --daemon-url http://127.0.0.1:7456`, czyli agent
  w OD widzi projekty/artefakty OD jako narzędzia MCP.
- **opencode (MA)**: MA sam wykrywa `opencode` na PATH (`opencode run --format json`, prompt na stdin).
- **Hermes**: MCP do OD można podpiąć komendą `od mcp install hermes` wewnątrz kontenera, albo wpisem
  `docker exec -i design-anim-open-design-1 od mcp --daemon-url http://127.0.0.1:7456` w konfiguracji MCP Hermesa.
- **Skille**: skill MA „motion-anything (router)" + `gsap`, `web-clone`, `web-to-design-md`, `web-shader-extractor`
  są w repo upstreamu (`skills/`). U nas: `motion-layer-integration` (jak wpiąć warstwę ruchu w projekt).

## Utrzymanie

| Co | Jak |
|---|---|
| Zmiana modelu/klucza | `OPENCODE_*` w env → Redeploy |
| Podbicie wersji upstreamu | `MA_REF` (branch/tag) w `motion-anything/Dockerfile`, `ghcr.io/nexu-io/od:latest` pobierany przy buildzie → Redeploy z brakiem cache |
| Logi | `docker compose logs -f open-design motion-anything` |
| Diagnostyka silnika | `docker compose exec open-design od --help`, `docker compose exec motion-anything opencode --version` |

## Pułapki (sprawdzone)

- **Busybox `od`** w obrazie OD koliduje z `od` CLI → shim obowiązkowy.
- **opencode jest glibc** → na Alpine (OD) `libc6-compat`, dlatego MA bazuje na Debianie.
- **motion-anything słucha tylko na 127.0.0.1** → bez caddy'ego w tym samym kontenerze nic z zewnątrz nie wejdzie
  (published port Docker nie dowiezie do loopbacku w netns kontenera).
- **`$` w env psuje interpolację compose** → dlatego hash bcrypt liczy się w entrypoincie z plaintextu,
  a nie wkleja do env.
- **Klucze OmniRoute** żyją w `~/.local/share/opencode/auth.json`, nie w `opencode.jsonc`.
