---
title: PTA Chat MCP
emoji: 🧳
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# PTA Chat MCP

Agoda's Personal Travel Assistant chat exposed as a remote **MCP** server.

Connect any MCP client (Cursor, Claude Desktop, etc.) to the endpoint below and
use the `plan_trip` tool to search hotels, flights, things to do, and build
itineraries through Agoda's PTA agent.

## Endpoint

```
https://<this-space>.hf.space/mcp
```

## MCP client config (Cursor / Claude Desktop)

```json
{
  "mcpServers": {
    "pta-chat": {
      "type": "http",
      "url": "https://<this-space>.hf.space/mcp"
    }
  }
}
```

## Tool

### `plan_trip(message, objective="itinerary")`

- `message` — free-text travel request
- `objective` — `"hotels" | "flights" | "activities" | "places" | "itinerary"`

Returns the assistant's reply text plus recommended items (hotels/activities/
flights) with title, rating, review score, price, reason, and a booking link.

## Notes

- The Space uses a session cookie (`PTA_COOKIE` secret) to authenticate against
  `agoda.com/pta/chat`. The cookie expires ~every 90 days.
- Free Spaces sleep after inactivity (~30s cold start on first request).
