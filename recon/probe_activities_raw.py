"""Dump raw activity card data so we can see what URL/coords fields activities carry."""
import json
import pathlib

from pta_mcp.pta_client import PtaClient
from pta_mcp.server import _renderprops

COOKIE = pathlib.Path("/Users/mdahiya/pta_mcp/secrets/cookies.txt")
client = PtaClient(COOKIE)
try:
    resp = client.plan_trip(
        "Yes. Plan Bangkok to Tokyo and Kyoto, Dec 9-15, 2026, as a 7-day first-time Japan itinerary. "
        "Include a day-by-day plan with places to visit, things to do, hotel area suggestions, "
        "and transport between cities.",
        title="MCP: itinerary",
    )
    print(f"events: {resp.raw_events} | widgets: {len(resp.widgets)} | textlen: {len(resp.text or '')}")

    found = 0
    for w in resp.widgets:
        props = _renderprops(w)
        if props is None:
            continue
        # Walk every list-valued key (same logic as _extract_cards)
        for key, val in props.items():
            if not isinstance(val, list):
                continue
            for item in val:
                if not isinstance(item, dict):
                    continue
                d = item.get("data") if isinstance(item.get("data"), dict) else item
                kind = d.get("place_type") or d.get("displayCategory") or item.get("type")
                # Heuristic: activity cards usually lack propertyLink + placeToken
                has_link = any(d.get(k) for k in ("propertyLink", "navUrl", "bookingUrl", "placeToken"))
                if not has_link:
                    found += 1
                    print("\n" + "=" * 80)
                    print(f"KEY={key!r} kind={kind!r} title={d.get('title') or d.get('name')!r}")
                    print("ALL KEYS:", sorted(d.keys()))
                    # Print URL-ish and geo fields
                    for fk in ("url", "link", "navUrl", "propertyLink", "bookingUrl", "activityUrl",
                               "landingUrl", "deeplink", "deepLink", "placeToken", "placeId",
                               "place_id", "latitude", "longitude", "lat", "lng", "address",
                               "location", "geo", "coordinates", "id", "activityId", "productId",
                               "code", "slug", "category", "displayCategory", "place_type"):
                        if fk in d:
                            v = d[fk]
                            if isinstance(v, (dict, list)):
                                v = json.dumps(v)[:300]
                            print(f"  {fk}: {v!r}")
                    # Save the first one fully
                    if found == 1:
                        pathlib.Path("/tmp/activity_raw.json").write_text(
                            json.dumps(d, indent=2, ensure_ascii=False)
                        )
                        print("  [saved full data to /tmp/activity_raw.json]")
    print(f"\n=== found {found} linkless cards ===")
except Exception:
    import traceback
    traceback.print_exc()
finally:
    client.close()
