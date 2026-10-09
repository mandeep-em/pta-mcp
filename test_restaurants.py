"""Live test: restaurants query through the public endpoint, confirm URLs present."""
import json
import httpx

URL = "https://mandeepmusepta-pta-chat.hf.space/mcp"
H = {"content-type": "application/json", "accept": "application/json, text/event-stream"}


def rpc(c, p, sid=None):
    h = dict(H)
    if sid:
        h["Mcp-Session-Id"] = sid
    r = c.post(URL, json=p, headers=h, timeout=200.0)
    for line in r.text.splitlines():
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip()), r.headers.get("Mcp-Session-Id")
            except json.JSONDecodeError:
                pass
    return None, r.headers.get("Mcp-Session-Id")


with httpx.Client() as c:
    _, sid = rpc(c, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                                "clientInfo": {"name": "e2e", "version": "1"}}})
    c.post(URL, json={"jsonrpc": "2.0", "method": "notifications/initialized"},
          headers={**H, "Mcp-Session-Id": sid}, timeout=30.0)
    resp, _ = rpc(c, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                     "params": {"name": "plan_trip", "arguments": {
                         "message": "Recommend restaurants in Tokyo near Shinjuku and Shibuya for dinner. Show names, cuisine and links.",
                         "objective": "activities"}}}, sid)
    for x in (resp or {}).get("result", {}).get("content", []):
        if x.get("type") == "text":
            print(x["text"])
