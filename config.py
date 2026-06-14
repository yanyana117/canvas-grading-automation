"""Central configuration, loaded entirely from environment variables.

Nothing secret is committed to this repository. Copy .env.example to .env
and fill in your own values, or export these variables in your shell before
running any script.
"""
import os


CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://canvas.example.edu/api/v1")
CANVAS_TOKEN = os.environ.get("CANVAS_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")

COURSE_ID = os.environ.get("COURSE_ID", "")
ASSIGNMENT_ID = os.environ.get("ASSIGNMENT_ID", "")
QUIZ_ID = os.environ.get("QUIZ_ID", "")

GITHUB_ORG = os.environ.get("GITHUB_ORG", "your-org")
REPO_PREFIX = os.environ.get("REPO_PREFIX", "course-labs-")


def require(name, value):
    """Fail fast with a clear message when a required variable is missing."""
    if not value:
        raise SystemExit(
            f"ERROR: environment variable {name} is not set. See .env.example."
        )
    return value
