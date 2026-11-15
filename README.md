# miniproject7RachelWhite: Practice Hub MCP Server

This is a [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that wraps the
**Practice Hub REST API** (`https://practice.fhsucyber.com/api/v1`). Once it is registered with
Claude Code, Claude can list, read, create, edit, and delete **your own** Practice Hub posts by
calling the server's tools. It does the same API calls as Mini Project 1, but an agent makes them.

The server is written with **FastMCP** from the official `mcp` Python SDK and talks to the API
with `httpx`. It uses the default **stdio** transport.

## Tools

| Tool | API call | What it does |
|------|----------|--------------|
| `list_posts(mine=False, tag=None)` | `GET /api/v1/posts?mine=…&tag=…` | Lists posts. `mine=True` returns only your posts. `tag` filters by tag. |
| `get_post(post_id)` | `GET /api/v1/posts/{id}` | Gets one post by id. |
| `create_post(title, body="", tags=None)` | `POST /api/v1/posts` | Creates a new post as you. |
| `update_post(post_id, title=None, body=None, tags=None)` | `PATCH /api/v1/posts/{id}` | Edits one of your posts. Only the fields you pass are changed. |
| `delete_post(post_id)` | `DELETE /api/v1/posts/{id}` | Deletes one of your posts. |

### Error handling

Every request goes through one helper, `_request()`. When something fails, the helper raises a
`PracticeHubError` with a readable message, and each tool catches it and **returns the message
as text**. Because the error is returned instead of raised, the server keeps running and Claude
can tell you what went wrong. Examples:

```
Error 403: Permission denied - you can only edit or delete your own posts. Server said: You can only modify your own posts.
Error 404: Not found - no post exists with that id. Server said: Post not found.
Error 401: Authentication failed - PRACTICE_API_TOKEN is missing, invalid, or expired.
```

Network failures, timeouts, and a missing token are handled the same way.

## Installation

Requires Python 3.10 or newer.

```bash
git clone <this repo>
cd miniproject7RachelWhite-main
python -m venv .venv
```

Activate the virtual environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

> Note: `requirements.txt` pins `mcp<2`. In version 2 of the SDK, `FastMCP` was renamed to
> `MCPServer`, and this project uses `FastMCP` as the assignment requires.

## Environment variables

The server reads its settings from the environment. **The token is never hard-coded** in this
repo, and `.env` files are listed in `.gitignore`.

| Variable | Required | Default |
|----------|----------|---------|
| `PRACTICE_API_TOKEN` | yes | none |
| `PRACTICE_API_URL` | no | `https://practice.fhsucyber.com` |

Set them in the shell you will start Claude Code from:

```powershell
# Windows PowerShell
$env:PRACTICE_API_TOKEN = "your-token-here"
$env:PRACTICE_API_URL = "https://practice.fhsucyber.com"
```

```bash
# macOS / Linux
export PRACTICE_API_TOKEN="your-token-here"
export PRACTICE_API_URL="https://practice.fhsucyber.com"
```

## Register with Claude Code

Run this from the project folder. It passes the variables from your current shell to the server
with `-e`, so the token is stored in your local Claude Code config and not in this repo.

```powershell
# Windows PowerShell
claude mcp add practice-hub -e PRACTICE_API_URL=$env:PRACTICE_API_URL -e PRACTICE_API_TOKEN=$env:PRACTICE_API_TOKEN -- "$PWD\.venv\Scripts\python.exe" "$PWD\server.py"
```

```bash
# macOS / Linux
claude mcp add practice-hub -e PRACTICE_API_URL="$PRACTICE_API_URL" -e PRACTICE_API_TOKEN="$PRACTICE_API_TOKEN" -- "$PWD/.venv/bin/python" "$PWD/server.py"
```

The general form is `claude mcp add practice-hub -e ... -- python server.py`. Using the venv's
Python and absolute paths means the server starts correctly no matter which folder Claude Code is
opened in.

Check that it connected:

```bash
claude mcp list
```

You should see `practice-hub: ... - ✓ Connected`. Inside Claude Code, `/mcp` shows the server and
its five tools.

## Acceptance test

The acceptance test is **read → create → modify, through the server**. Start Claude Code
(`claude`) and send these prompts one at a time:

1. **Read:** `Using the practice-hub server, list my posts.`
   Claude calls `list_posts` with `mine=true` and shows your posts.
2. **Create:** `Create a new post titled "Hello from my MCP server" with body "Posted by Claude Code through my own MCP server." and tags mcp and python.`
   Claude calls `create_post` and reports the new post's id.
3. **Modify:** `Change the title of that post to "Hello from my MCP server (edited)".`
   Claude calls `update_post` and shows the updated post.
4. **Optional error check:** `Get post 999999.` Claude calls `get_post` and gets back the
   404 message, and the server keeps running.

Approve each tool call when Claude Code asks. Confirm the changes on the Practice Hub website.

A transcript of my run is in [`docs/acceptance-test.md`](docs/acceptance-test.md), and screenshots
are in [`docs/`](docs/).

### Testing without Claude Code

To check the tools without an agent, call the functions from Python:

```bash
python -c "import server; print(server.list_posts(mine=True))"
```

## AI Usage

I used Claude Code (Claude Opus 5.5) as an assistant on this project. I gave it the assignment
and my Mini Project 1 client, and it helped me:

- draft `server.py`, reusing the endpoint and error-handling design from my Mini Project 1 client
  and moving it from `requests` to `httpx` and FastMCP tools,
- find out that `mcp` 2.x renamed `FastMCP`, so I pinned `mcp<2` in `requirements.txt`,
- smoke-test every tool against the live API, including the 403 and 404 cases, and
- draft this README.

I reviewed and ran all of the code myself, did the acceptance test through Claude Code, and
checked the results on the Practice Hub site.
