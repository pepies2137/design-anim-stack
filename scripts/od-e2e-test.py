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

agents = tool("list_agents", {})
txt = json.dumps(agents)
print("list_agents (fragment):", txt[:300])

proj = tool("create_project", {"name": "test-silnika-opencode", "id": "test-silnika-opencode"})
print("create_project:", json.dumps(proj)[:300])

run = tool("start_run", {"project": "test-silnika-opencode", "agent": "opencode",
                         "prompt": "Krotki landing hero: naglowek, podtytul, jeden przycisk. Czysty HTML+CSS, bez zewnetrznych zasobow."})
print("start_run:", json.dumps(run)[:400])

rid = None
try:
    payload = run.get("result", {})
    blob = json.dumps(payload)
    import re
    m = re.search(r'"(runId|id)"\s*:\s*"([^"]+)"', blob)
    if m:
        rid = m.group(2)
except Exception:
    pass
if not rid:
    print("BRAK runId — koncze"); p.kill(); sys.exit(2)

for i in range(40):
    time.sleep(15)
    st = tool("get_run", {"runId": rid})
    blob = json.dumps(st)
    status = None
    import re
    m = re.search(r'"status"\s*:\s*"([a-z]+)"', blob)
    if m:
        status = m.group(1)
    print(f"[{i*15+15}s] status={status}")
    if status in ("succeeded", "failed", "canceled"):
        print("FINAL:", blob[:1500])
        break
p.kill()
