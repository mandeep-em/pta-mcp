# PTA Chat MCP

Exposes Agoda's **Personal Travel Assistant** chat (`agoda.com/pta/chat`) as a
single MCP tool, `plan_trip`, so any MCP client (Cursor, Claude Desktop, etc.)
can plan trips — search hotels, flights, things to do, places to visit, and
build itineraries — through Agoda's PTA agent.

## How it works

```
MCP client ──(MCP stdio)──► pta_mcp server ──(HTTPS + cookies)──► agoda.com/pta/chat
                            tool: plan_trip     1. POST /api/conversations   (create)
                                                2. POST /api/.../messages  (SSE, buffered)
```

The server creates a PTA conversation, sends the user's message, buffers the
streamed (SSE) reply into a single text response, extracts any hotel/activity/
flight cards the agent produced, and returns them.

## Auth

The PTA chat requires a logged-in Agoda session. The programmatic login
(`POST /ul/api/v1/signin`) is gated by **reCAPTCHA**, so this server uses
**manually exported browser cookies** instead.

1. Sign in at `agoda.com/pta/chat` in your browser (solve the captcha once).
2. Export the `Cookie` request header for `www.agoda.com` (browser dev tools →
   Network → any request → Request Headers → `cookie`).
3. Save it to `secrets/cookies.txt` (one line, the full cookie header value).

The session cookies last ~90 days. When they expire, re-export.

`secrets/` is gitignored — credentials are never committed.

## Install & run

```bash
uv sync
uv run python -m pta_mcp.server        # stdio MCP server
uv run mcp dev pta_mcp.server:mcp      # MCP inspector (browser UI)
```

## Cursor config

Add to `~/.cursor/mcp.json` (or the project `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "pta-chat": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/mdahiya/pta_mcp", "python", "-m", "pta_mcp.server"]
    }
  }
}
```

## Tool

### `plan_trip(message, objective="itinerary")`

- `message` — free-text travel request, e.g. `"Plan a 5-day Bali trip in December, find hotels and activities."`
- `objective` — hint: `"hotels" | "flights" | "activities" | "places" | "itinerary"`

Returns the assistant's reply text plus a compact list of recommended items
(hotels/activities/flights) with title, rating, review score, price, and reason.

## Project layout

```
pta_mcp/
  __init__.py
  pta_client.py     # PTA Chat HTTP/SSE client
  server.py         # MCP server + plan_trip tool
secrets/            # gitignored
  cookies.txt       # exported browser cookies
  credentials.json  # (optional) email/password for future automation
recon/              # M0 recon scripts + findings (not part of the server)
```

## Status

- ✅ M0 recon — login API + PTA chat API contract mapped
- ✅ M1 local server — `plan_trip` tool working end-to-end (buffered SSE, card extraction)
- ⬜ M2 automated login — blocked by reCAPTCHA (manual cookie export for now)
- ⬜ M3 public hosting — deferred
