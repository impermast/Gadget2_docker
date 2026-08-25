# MCP Tools

This project has the **fetch-mcp** MCP server installed and available for use.
Server name: `github.com/zcaceres/fetch-mcp`

## When to use

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