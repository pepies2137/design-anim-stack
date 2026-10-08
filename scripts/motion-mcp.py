#!/usr/bin/env python3
"""motion-mcp — serwer MCP (stdio) dla motion-anything.

Po co: motion-anything (upstream nexu-io/motion-anything) NIE ma wlasnego MCP — jest CLI + HTTP.
Ten serwer wystawia jego biblioteke przepisow jako narzedzia MCP, zeby agenci (opencode, Hermes)
mogli sami dobierac i wyciagac przepisy ruchu w trakcie pracy nad kodem.

Narzedzia:
  motion_list     [query]     — lista przepisow (id, kategoria, tagi, opis); query = filtr po slowie
  motion_recipe   {id}        — pelna tresc przepisu: SKILL.md + implementacje (.js/.css/.html)
  motion_add      {id, dir?}  — eksport przepisu (bundle 4 plikow) i zwrot zawartosci do wklejenia
  motion_ready    {}          — czy kontener/kokpit motion-anything zyje

Transport: JSON-RPC 2.0 po stdio (MCP). Zero zaleznosci — stdlib. Kontener szukany po labelach
compose, wiec przezyje zmiane nazwy nadanej przez Dokploy.
"""
import json
import subprocess
import sys

CONTAINER_SERVICE = "motion-anything"
MA_CLI = "node /app/cli/bin/motion.js"
EXPORT_DIR_IN_CONTAINER = "/app/app/user-skills/motion-skills"


def sh(cmd, timeout=120, cwd=None):
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout po {timeout}s"
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)


def container():
    code, out, _ = sh("docker ps -q --filter label=com.docker.compose.service=" + CONTAINER_SERVICE)
    cid = out.strip().split("\n")[0] if code == 0 else ""
    return cid or None


def docker(args, timeout=120):
    cid = container()
    if not cid:
        return 1, "", "brak dzialajacego kontenera motion-anything (docker ps)"
    return sh(["docker", "exec", "-i", cid] + args, timeout=timeout)


def tool_list(query=""):
    code, out, err = docker(["sh", "-c", MA_CLI + " list"], timeout=180)
    if code != 0:
        return f"BLAD listy przepisow: {err or out}"
    out = out.replace("\r", "")
    if not query:
        return out
    q = query.lower()
    blocks = out.split("\n\n")
    hits = [b for b in blocks if q in b.lower()]
    if not hits:
        return f"Brak przepisow pasujacych do '{query}'. Uzyj motion_list bez filtra."
    return f"Przepisy pasujace do '{query}' ({len(hits)}):\n\n" + "\n\n".join(hits)


def tool_recipe(recipe_id):
    rid = (recipe_id or "").strip().strip("/")
    if not rid or "/" in rid or ".." in rid:
        return "BLAD: podaj samo id przepisu, np. plasma"
    code, out, err = docker(["sh", "-c", f"ls -1 /app/recipes/*/{rid} 2>/dev/null | head -1"])
    base = out.strip()
    if not base:
        # przepisy moga lezec tez w eksportach user-skills
        code, out, err = docker(["sh", "-c", f"ls -1 {EXPORT_DIR_IN_CONTAINER}/{rid} 2>/dev/null | head -1"])
        base = out.strip()
    if not base:
        return f"BLAD: nie znalazlem przepisu '{rid}'. Sprawdz motion_list."
    code, listing, _ = docker(["sh", "-c", f"find {EXPORT_DIR_IN_CONTAINER}/{rid} -type f 2>/dev/null || true"])
    code2, files, _ = docker(["sh", "-c", f"cd {base} && for f in *; do echo \"===== $f\"; cat \"$f\"; echo; done"])
    return f"Przepis '{rid}' (katalog: {base})\n\n{files[:60000]}"


def tool_add(recipe_id):
    rid = (recipe_id or "").strip().strip("/")
    if not rid or "/" in rid or ".." in rid:
        return "BLAD: podaj samo id przepisu, np. plasma"
    code, out, err = docker(["sh", "-c", f"cd /app/app/user-skills && {MA_CLI} add {rid}"], timeout=180)
    if code != 0:
        return f"BLAD eksportu '{rid}': {err or out}"
    code, files, _ = docker(["sh", "-c", f"cd {EXPORT_DIR_IN_CONTAINER}/{rid} && for f in *; do echo \"===== {rid}/$f\"; cat \"$f\"; echo; done"])
    return (f"Wyeksportowany przepis '{rid}' (bundle: SKILL.md + implementacja + preview).\n"
            f"Skopiuj pliki do projektu (np. src/motion/<nazwa>/):\n\n{files[:60000]}")


def tool_ready():
    cid = container()
    if not cid:
        return "motion-anything: KONTENER NIE DZIALA"
    code, out, _ = docker(["sh", "-c", "opencode --version 2>/dev/null; node -e \"console.log(require('/app/cli/package.json').version)\""])
    return f"motion-anything OK (kontener {cid[:12]}), wersja: {out.strip()}"


TOOLS = {
    "motion_list": {
        "fn": tool_list,
        "desc": ("Lista przepisow ruchu z biblioteki motion-anything (id, kategoria, tagi, opis). "
                 "Uzyj zanim cokolwiek animujesz — dobierz gotowy przepis zamiast wymyslac easingi. "
                 "Opcjonalny argument 'query' filtruje po slowie (np. 'plasma', 'zoom', 'reveal')."),
        "schema": {"type": "object", "properties": {"query": {"type": "string", "description": "filtr, np. plasma"}}},
        "args": lambda a: (a.get("query", ""),),
    },
    "motion_recipe": {
        "fn": tool_recipe,
        "desc": ("Pelna tresc przepisu: SKILL.md (kiedy uzywac, czego nie robic), implementacja CSS/JS "
                 "i preview.html. Uzyj, gdy chcesz wdrozyc konkretny efekt w projekcie."),
        "schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
        "args": lambda a: (a.get("id", ""),),
    },
    "motion_add": {
        "fn": tool_add,
        "desc": ("Eksportuje przepis jako bundle do wklejenia w repo projektu (zwraca tresc plikow: "
                 "SKILL.md, .css, .js, preview.html). To sposob na uzycie biblioteki w kodzie produkcyjnym."),
        "schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
        "args": lambda a: (a.get("id", ""),),
    },
    "motion_ready": {
        "fn": tool_ready,
        "desc": "Sprawdza, czy biblioteka motion-anything (kontener + silnik opencode) odpowiada.",
        "schema": {"type": "object", "properties": {}},
        "args": lambda a: (),
    },
}


def handle(req):
    method = req.get("method")
    rid = req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "motion-anything", "version": "0.1.0"},
            "instructions": ("Biblioteka ruchu motion-anything: wybieraj gotowe przepisy (motion_list -> motion_recipe -> "
                             "motion_add) zamiast wymyslac animacje od zera. Przepisy maja wbudowane "
                             "prefers-reduced-motion i ograniczenia (restraint) opisane w SKILL.md."),
        }}
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": [
            {"name": n, "description": t["desc"], "inputSchema": t["schema"]} for n, t in TOOLS.items()
        ]}}
    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        t = TOOLS.get(name)
        if not t:
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": f"nieznane narzedzie: {name}"}], "isError": True}}
        try:
            text = t["fn"](*t["args"](args))
        except Exception as e:  # noqa: BLE001
            text = f"BLAD narzedzia {name}: {e}"
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": text}], "isError": True}}
        return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": text}]}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"nieznana metoda: {method}"}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
