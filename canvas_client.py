"""Minimal Canvas LMS REST API client: authenticated session and pagination."""
import requests

import config


def make_session():
    token = config.require("CANVAS_TOKEN", config.CANVAS_TOKEN)
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def get_pages(session, url, params=None):
    """Yield the parsed JSON of every page of a Canvas list endpoint.

    Canvas paginates with RFC 5988 Link headers; this follows the
    ``next`` link until there are no more pages.
    """
    params = dict(params or {})
    params.setdefault("per_page", 100)
    while url:
        r = session.get(url, params=params)
        r.raise_for_status()
        yield r.json()
        url = r.links.get("next", {}).get("url")
        params = {}
