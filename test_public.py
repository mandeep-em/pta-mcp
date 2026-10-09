"""Live end-to-end test of the public pta-chat MCP endpoint.

Runs a full streamable-HTTP MCP session:
  initialize -> notifications/initialized -> tools/list -> tools/call plan_trip
and prints the assistant reply + extracted hotel cards with links.
"""
import json
import sys
import httpx

URL = "https://mandeepmusepta-pta-chat.hf.space/mcp"
HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/event-stream",
}


def parse_sse(text: str) -> dict | None:
    for line in text.splitlines():
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except json.JSONDecodeError:
                pass
    return None


def rpc(client: httpx.Client, payload: dict, session_id: str | None = None) -> tuple[dict | None, str | None]:
    headers = dict(HEADERS)
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    r = client.post(URL, json=payload, headers=headers, timeout=150.0)
    sid = r.headers.get("Mcp-Session-Id")
    return parse_sse(r.text), sid


def main() -> None:
    with httpx.Client() as client:
        print("=== 1. initialize ===")
        resp, sid = rpc(client, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "e2e-test", "version": "1"}},
        })
        print("session id:", sid)
        print("server:", (resp or {}).get("result", {}).get("serverInfo"))
        if not sid:
            print("ERROR: no session id; raw:", resp); sys.exit(1)

        print("\n=== 2. notifications/initialized ===")
        client.post(URL, json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                     headers={**HEADERS, "Mcp-Session-Id": sid}, timeout=30.0)

        print("\n=== 3. tools/list ===")
        resp, _ = rpc(client, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, sid)
        tools = (resp or {}).get("result", {}).get("tools", [])
        print("tools:", [t["name"] for t in tools])

        print("\n=== 4. tools/call plan_trip ===")
        resp, _ = rpc(client, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "plan_trip", "arguments": {
                "message": "Find me 3 hotels in Tokyo for Dec 9-11 2026, 2 guests. Show hotel names and links.",
                "objective": "hotels",
            }},
        }, sid)
        result = (resp or {}).get("result", {})
        content = result.get("content", [])
        for c in content:
            if c.get("type") == "text":
                print(c["text"])
        if result.get("isError"):
            print("ERROR response:", result)


if __name__ == "__main__":
    main()
