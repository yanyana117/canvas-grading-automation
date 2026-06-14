"""Minimal GitHub REST API client with a read-only safety guard.

Grading must never be able to modify student repositories, so the client
refuses to run if the supplied token carries any write capable scope.
"""
import sys
import time

import requests

import config

GITHUB_API = "https://api.github.com"


def make_session():
    token = config.require("GITHUB_TOKEN", config.GITHUB_TOKEN)
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    return s


def assert_read_only(session):
    """Exit unless the token authenticates and has only read scopes."""
    r = session.get(f"{GITHUB_API}/user")
    if r.status_code != 200:
        sys.exit(f"Error: token cannot authenticate (status {r.status_code}).")
    scopes = r.headers.get("X-OAuth-Scopes", "")
    forbidden = ("repo", "write", "admin", "delete")
    bad = [s for s in scopes.split(",")
           if any(f in s.strip().lower() for f in forbidden)]
    if bad:
        sys.exit(f"Refusing to run: token has write capable scopes: {bad}")
    print("GitHub token check passed (read only).")


def gh_get(session, url):
    """GET with simple rate-limit aware retry. Returns (status, json)."""
    r = None
    for _ in range(3):
        r = session.get(url, timeout=30)
        if r.status_code == 403 and "rate limit" in r.text.lower():
            reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 60))
            time.sleep(max(1, reset - time.time()) + 1)
            continue
        return r.status_code, (r.json() if r.content else None)
    return (r.status_code if r is not None else 0), None
