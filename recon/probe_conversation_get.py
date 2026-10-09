"""Probe GET /conversations/{cid} to learn the fallback-response structure."""
import json
import pathlib

from pta_mcp.pta_client import PtaClient, CREATE_URL, SEND_URL_TMPL

COOKIE = pathlib.Path("/Users/mdahiya/pta_mcp/secrets/cookies.txt")
client = PtaClient(COOKIE)
try:
    cid = client.create_conversation(title="MCP: probe")
    print("created conversation:", cid)

    # Send a short message via SSE (completes fast)
    resp = client.send_message(cid, "Suggest 2 hotels in Tokyo for Dec 10-12 2026, 2 guests.")
    print("SSE text len:", len(resp.text), "| widgets:", len(resp.widgets), "| msg_id:", resp.message_id)

    # Now GET the conversation
    get_url = f"https://www.agoda.com/en-gb/pta/chat/api/conversations/{cid}"
    r = client._client.get(get_url, headers={"accept": "application/json, text/plain, */*"})
    print("GET status:", r.status_code)
    pathlib.Path("/tmp/conversation_get.json").write_text(r.text)
    try:
        data = r.json()
        print("GET top-level keys:", list(data.keys()) if isinstance(data, dict) else type(data))
        # Print structure summary
        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
    except Exception as e:
        print("json parse error:", e, "| body:", r.text[:1000])
finally:
    client.close()
