# MCP Tools

This project has two MCP servers available for use.

## Telegram sender (global)

Server name: `tg-notify`

Global zero-dependency MCP server for sending Telegram notifications from any
project on this machine. Server: `/home/kds/Документы/Cline/MCP/tg-notify/`,
registered in global `cline_mcp_settings.json`. Credentials are global:
`~/.cline/tg-notify/telegram.conf` (same bot as `nbody/tg/telegram.conf`).

Tool: `send_message` — params: `text` (required, max 4000), optional
`parse_mode` (`Markdown`/`HTML`), optional `disable_notification` (silent).
Use for short status/result notifications at the end of a task — not for
periodic progress spam, and never as a substitute for the run_sim.sh automatic
START/FINISH/ERROR flow.

## Fetch (global)

Server name: `github.com/zcaceres/fetch-mcp`

## When to use (fetch-mcp)

Use MCP fetch tools whenever you need to retrieve web content during a task:

- fetching documentation, API references, or tutorials;
- checking for updated versions of GADGET-2 / GIZMO / GalIC;
- downloading example configurations or parameter files from the web;
- reading README or wiki pages of third-party tools;
- inspecting JSON/YAML endpoints for simulation metadata.

## Available tools

| Tool | Purpose |
|------|---------|
| `fetch_html` | Raw HTML of a page |
| `fetch_markdown` | Page converted to Markdown |
| `fetch_txt` | Plain text (no HTML/scripts/styles) |
| `fetch_json` | JSON response from a URL |
| `fetch_readable` | Article content via Mozilla Readability (strips nav/ads) — ideal for blog posts and docs |
| `fetch_youtube_transcript` | YouTube video transcript (supports `lang` parameter) |

All tools accept: `url` (required), `headers`, `max_length`, `start_index`, `proxy`.

## Usage tips

- Prefer `fetch_readable` for long documentation pages — it strips boilerplate.
- Use `fetch_json` for REST API calls.
- Use `max_length` to limit output and avoid context overflow.
- The server is **read-only** — it only fetches data, never modifies anything.