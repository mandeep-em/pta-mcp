"""Probe message-fetch endpoints to find where the completed response lives."""
import json
import pathlib

from pta_mcp.pta_client import PtaClient

COOKIE = pathlib.Path("/Users/mdahiya/pta_mcp/secrets/cookies.txt")
client = PtaClient(COOKIE)
try:
    cid = client.create_conversation(title="MCP: probe2")
    print("cid:", cid)
    resp = client.send_message(cid, "Suggest 2 hotels in Tokyo for Dec 10-12 2026, 2 guests.")
    mid = resp.message_id
    print("msg_id:", mid, "| text len:", len(resp.text), "| widgets:", len(resp.widgets))

    base = "https://www.agoda.com/en-gb/pta/chat/api/conversations"
    candidates = [
        f"{base}/{cid}/messages",
        f"{base}/{cid}/messages/{mid}",
        f"{base}/{cid}/{mid}",
        f"{base}/{cid}",
        f"{base}/{cid}/messages?messageId={mid}",
    ]
    for url in candidates:
        try:
            r = client._client.get(url, headers={"accept": "application/json, text/plain, */*"})
            print(f"\n[{r.status_code}] {url}")
            if r.status_code == 200:
                txt = r.text
                # Heuristic: does it contain widgetData or the reply text?
                has_widget = "widgetData" in txt
                has_text = "content" in txt and "text" in txt
                print(f"  len={len(txt)} widgetData={has_widget} content/text={has_text}")
                print("  ", txt[:600].replace("\n", " "))
        except Exception as e:
            print(f"  ERR {e}")
finally:
    client.close()
