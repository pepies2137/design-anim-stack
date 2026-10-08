#!/usr/bin/env python3
"""E2E test silnika OpenDesign przez MCP (stdio): create_project -> start_run -> get_run.
Uruchamia sie z tego boxa; MCP startuje w kontenerze (wrapper ~/.local/bin/od-mcp-stdio)."""
import json, subprocess, sys, time

CMD = ["/home/m75q/.local/bin/od-mcp-stdio"]
p = subprocess.Popen(CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)

_id = 0
def call(method, params=None, timeout=120):
    global _id
    _id += 1
    req = {"jsonrpc": "2.0", "id": _id, "method": method}
    if params is not None:
        req["params"] = params
    p.stdin.write(json.dumps(req) + "\n"); p.stdin.flush()
    t0 = time.time()
    while time.time() - t0 < timeout:
        line = p.stdout.readline()
        if not line:
            return {"error": "EOF"}
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("id") == _id:
            return d
    return {"error": "timeout"}

def tool(name, args, timeout=600):
    return call("tools/call", {"name": name, "arguments": args}, timeout=timeout)

init = call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "hermes-e2e", "version": "1"}})
print("initialize:", json.dumps(init.get("result", {}).get("serverInfo")))

def tool_text(name, args, timeout=600):
    """Wywoluje narzedzie i zwraca sparsowany JSON z jego odpowiedzi (MCP pakuje wynik w content[].text)."""
    r = tool(name, args, timeout=timeout)
    res = r.get("result", {})
    txt = "".join(c.get("text", "") for c in res.get("content", []) if isinstance(c, dict))
    if res.get("isError"):
        print(f"  ! {name}: {txt[:200]}")
        return None
    try:
        return json.loads(txt)
    except Exception:
        print(f"  ? {name}: {txt[:200]}")
        return None

agents = tool_text("list_agents", {})
if agents:
    print("silniki dostepne:", [a.get("id") for a in agents.get("agents", [])])

proj = tool_text("create_project", {"name": "test-silnika-opencode", "id": "test-silnika-opencode"})
print("create_project:", (proj or {}).get("project", {}).get("id"))

run = tool_text("start_run", {"project": "test-silnika-opencode", "agent": "opencode",
                              "prompt": "Krotki landing hero: naglowek, podtytul, jeden przycisk. Czysty HTML+CSS, bez zewnetrznych zasobow."})
if not run:
    print("BRAK runu — koncze"); p.kill(); sys.exit(2)
rid = run.get("runId")
status = run.get("status")
print("start_run:", rid, "| status:", status)

for i in range(40):
    if status in ("succeeded", "failed", "canceled"):
        break
    time.sleep(15)
    st = tool_text("get_run", {"runId": rid}) or {}
    status = st.get("status")
    print(f"[{(i + 1) * 15}s] status={status} | files={len(st.get('files') or [])} | err={str(st.get('error'))[:120]}")

print("FINAL:", json.dumps({"runId": rid, "status": status, "files": (tool_text('get_run', {'runId': rid}) or {}).get('files')})[:800])
p.kill()
sys.exit(0 if status == "succeeded" else 1)

