"""Verify the updated _extract_cards picks up the placeToken URL for restaurants."""
import pathlib
from pta_mcp.pta_client import PtaClient
from pta_mcp.server import _extract_cards, _format_card, _format_response

COOKIE = pathlib.Path("/Users/mdahiya/pta_mcp/secrets/cookies.txt")
client = PtaClient(COOKIE)
cid = client.create_conversation(title="verify placeToken")
resp = client.send_message(
    cid,
    "Recommend restaurants in Tokyo near Shinjuku and Shibuya for dinner. Show names, cuisine and links.",
)
print(f"widgets: {len(resp.widgets)}")
cards = _extract_cards(resp.widgets)
print(f"cards: {len(cards)}\n")
for i, c in enumerate(cards, 1):
    print(_format_card(i, c))
    print(f"   [meta] kind={c.get('kind')!r} category={c.get('category')!r} "
          f"place_id={c.get('place_id')!r} lat={c.get('latitude')} lng={c.get('longitude')}")
    print()
client.close()
