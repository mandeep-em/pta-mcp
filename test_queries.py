"""Run several plan_trip queries (flights, activities, restaurants, itinerary)
through the public pta-chat MCP endpoint, each in its own session.
"""
import json
import sys
import httpx

URL = "https://mandeepmusepta-pta-chat.hf.space/mcp"
HEADERS = {"content-type": "application/json", "accept": "application/json, text/event-stream"}


def parse_sse(text: str) -> dict | None:
    for line in text.splitlines():
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except json.JSONDecodeError:
                pass
    return None


def rpc(client, payload, sid=None):
    headers = dict(HEADERS)
    if sid:
        headers["Mcp-Session-Id"] = sid
    r = client.post(URL, json=payload, headers=headers, timeout=200.0)
    return parse_sse(r.text), r.headers.get("Mcp-Session-Id")


def run_query(label, message, objective):
    print("\n" + "=" * 78)
    print(f"QUERY: {label}  (objective={objective})")
    print("=" * 78)
    with httpx.Client() as client:
        resp, sid = rpc(client, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "e2e", "version": "1"}}})
        if not sid:
            print("FAILED initialize:", resp); return
        client.post(URL, json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                     headers={**HEADERS, "Mcp-Session-Id": sid}, timeout=30.0)
        resp, _ = rpc(client, {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "plan_trip", "arguments": {"message": message, "objective": objective}}}, sid)
        result = (resp or {}).get("result", {})
        for c in result.get("content", []):
            if c.get("type") == "text":
                print(c["text"])
        if result.get("isError"):
            print("ERROR:", result)


def main():
    run_query("FLIGHTS",
               "Find flights from Bangkok (BKK) to Tokyo (NRT) on Dec 9 2026, returning Dec 11, 2 passengers. Show airline, route, times and links.",
               "flights")
    run_query("ACTIVITIES",
               "Find things to do in Tokyo for 3 days in December. Show activity names, ratings and booking links.",
               "activities")
    run_query("RESTAURANTS",
               "Recommend restaurants in Tokyo near Shinjuku and Shibuya for dinner. Show names, cuisine and links if available.",
               "activities")
    run_query("ITINERARY",
               "Plan a 3-day Tokyo trip in December 2026. Include hotels, things to do each day, and how to get around.",
               "itinerary")


if __name__ == "__main__":
    main()
