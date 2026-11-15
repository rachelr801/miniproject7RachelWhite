# INF601 - Advanced Programming in Python
# Rachel White
# Mini Project 7

"""MCP server that wraps the Practice Hub REST API.

Exposes five tools (list_posts, get_post, create_post, update_post,
delete_post) so an agent such as Claude Code can read, create, and modify
your own posts on the Practice Hub. Runs over stdio, the default transport.

Configuration comes from environment variables, never from this file:
    PRACTICE_API_URL    base URL of the API (default https://practice.fhsucyber.com)
    PRACTICE_API_TOKEN  your personal API token (required)
"""

import os

import httpx
from mcp.server.fastmcp import FastMCP

DEFAULT_API_URL = "https://practice.fhsucyber.com"
API_URL = os.environ.get("PRACTICE_API_URL", DEFAULT_API_URL).rstrip("/")
API_TOKEN = os.environ.get("PRACTICE_API_TOKEN")
TIMEOUT_SECONDS = 15.0

# Friendly explanations for the status codes the Practice Hub returns.
ERROR_MESSAGES = {
    400: "Bad request - the API could not understand the data that was sent.",
    401: "Authentication failed - PRACTICE_API_TOKEN is missing, invalid, or expired.",
    403: "Permission denied - you can only edit or delete your own posts.",
    404: "Not found - no post exists with that id.",
    422: "Validation failed - check the title, body, and tags you provided.",
    429: "Rate limited - too many requests, wait a moment and try again.",
}

mcp = FastMCP("practice-hub")


class PracticeHubError(Exception):
    """Raised when a Practice Hub request fails; the message is safe to show the model."""


def _request(method: str, path: str, **kwargs):
    """Send one request to the Practice Hub and return the parsed JSON body.

    Raises PracticeHubError with a readable message for any failure, so the
    tools can turn it into a normal return value instead of crashing.
    """
    if not API_TOKEN:
        raise PracticeHubError(
            "PRACTICE_API_TOKEN is not set. Set it in the environment of the MCP "
            "server (for example with `claude mcp add ... -e PRACTICE_API_TOKEN=...`)."
        )

    headers = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}
    try:
        resp = httpx.request(
            method, f"{API_URL}{path}", headers=headers, timeout=TIMEOUT_SECONDS, **kwargs
        )
    except httpx.TimeoutException:
        raise PracticeHubError(f"The request to {API_URL} timed out after {TIMEOUT_SECONDS:.0f}s.")
    except httpx.HTTPError as e:
        raise PracticeHubError(f"Could not reach the Practice Hub at {API_URL}: {e}")

    if resp.is_success:
        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return resp.text

    # Pull the server's own explanation out of the error body if there is one.
    detail = None
    try:
        body = resp.json()
        if isinstance(body, dict):
            detail = body.get("error") or body.get("message") or body.get("detail")
    except ValueError:
        detail = resp.text.strip()[:200] or None

    message = ERROR_MESSAGES.get(resp.status_code, "The Practice Hub API returned an error.")
    message = f"Error {resp.status_code}: {message}"
    if detail:
        message += f" Server said: {detail}"
    raise PracticeHubError(message)


@mcp.tool()
def list_posts(mine: bool = False, tag: str | None = None) -> list | str:
    """List posts on the Practice Hub.

    Use this to browse posts or to find the id of a post before reading,
    editing, or deleting it.

    Args:
        mine: If True, return only posts written by the current user (the
            token owner). Use mine=True whenever the user says "my posts".
        tag: Optional tag name; only posts with this tag are returned.

    Returns a list of post objects (id, title, body, tags, author, ...) or an
    error message string if the request failed.
    """
    params = {"mine": str(mine).lower()}
    if tag:
        params["tag"] = tag
    try:
        return _request("GET", "/api/v1/posts", params=params)
    except PracticeHubError as e:
        return str(e)


@mcp.tool()
def get_post(post_id: int) -> dict | str:
    """Get a single Practice Hub post by its numeric id.

    Args:
        post_id: The id of the post to fetch (see list_posts for ids).

    Returns the full post object, or an error message string (for example
    when no post has that id).
    """
    try:
        return _request("GET", f"/api/v1/posts/{post_id}")
    except PracticeHubError as e:
        return str(e)


@mcp.tool()
def create_post(title: str, body: str = "", tags: list[str] | None = None) -> dict | str:
    """Create a new post on the Practice Hub as the current user.

    Args:
        title: Title of the new post (required).
        body: Text content of the post.
        tags: Optional list of tag names, e.g. ["mcp", "python"].

    Returns the newly created post (including its new id), or an error
    message string if the API rejected it.
    """
    payload = {"title": title, "body": body, "tags": tags or []}
    try:
        return _request("POST", "/api/v1/posts", json=payload)
    except PracticeHubError as e:
        return str(e)


@mcp.tool()
def update_post(
    post_id: int,
    title: str | None = None,
    body: str | None = None,
    tags: list[str] | None = None,
) -> dict | str:
    """Edit one of the current user's own posts. Only the fields given are changed.

    You can only modify posts you wrote; editing someone else's post returns
    a permission-denied message.

    Args:
        post_id: The id of the post to edit.
        title: New title, or omit to keep the current one.
        body: New body text, or omit to keep the current one.
        tags: New full list of tags (replaces the old list), or omit to keep them.

    Returns the updated post, or an error message string.
    """
    payload = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    if tags is not None:
        payload["tags"] = tags
    if not payload:
        return "Nothing to update - provide at least one of title, body, or tags."
    try:
        return _request("PATCH", f"/api/v1/posts/{post_id}", json=payload)
    except PracticeHubError as e:
        return str(e)


@mcp.tool()
def delete_post(post_id: int) -> str:
    """Permanently delete one of the current user's own posts.

    This cannot be undone, so only call it when the user clearly asked to
    delete that specific post. Deleting someone else's post returns a
    permission-denied message.

    Args:
        post_id: The id of the post to delete.

    Returns a confirmation message, or an error message string.
    """
    try:
        _request("DELETE", f"/api/v1/posts/{post_id}")
    except PracticeHubError as e:
        return str(e)
    return f"Post {post_id} was deleted."


if __name__ == "__main__":
    # stdio is the default transport, which is what `claude mcp add ... -- python server.py` expects.
    mcp.run()
