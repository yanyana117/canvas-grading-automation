"""Unit tests for the pure grading-logic functions.

These cover the parts where a wrong answer would silently mis-grade a real
student: detecting which release denotes the target lab, choosing among
several releases, and mapping a lateness in hours to a penalty bracket.
"""
import fetch_github_late_times as g


class TestLabMarker:
    def test_accepts_common_lab_spellings(self):
        for tag in ["lab4", "Lab 4", "lab-4", "lab_4", "LAB04", "L4", "v4", "4.0"]:
            assert g.is_strong_lab_marker(tag, 4), tag

    def test_rejects_other_labs(self):
        for tag in ["lab3", "Lab 5", "lab40", "L3"]:
            assert not g.is_strong_lab_marker(tag, 4), tag

    def test_patch_version_is_not_mistaken_for_lab(self):
        # v1.0.4 / v1.4 must NOT count as lab 4
        assert not g.is_strong_lab_marker("v1.0.4", 4)
        assert not g.is_strong_lab_marker("v1.4", 4)

    def test_empty(self):
        assert not g.is_strong_lab_marker("", 4)


class TestPickLabRelease:
    def test_needs_review_when_no_strong_marker(self):
        rel, note = g.pick_lab_release([{"tag_name": "v1.0.0"}], 4)
        assert rel is None and note.startswith("NEEDS_REVIEW")

    def test_picks_earliest_to_avoid_penalizing_a_refix(self):
        releases = [
            {"tag_name": "lab4", "published_at": "2026-05-10T00:00:00Z"},
            {"tag_name": "lab4-fix", "published_at": "2026-05-03T00:00:00Z"},
        ]
        rel, note = g.pick_lab_release(releases, 4)
        assert rel["published_at"] == "2026-05-03T00:00:00Z"
        assert "MULTI" in note

    def test_ignores_unrelated_releases(self):
        releases = [
            {"tag_name": "lab3", "published_at": "2026-04-20T00:00:00Z"},
            {"tag_name": "lab4", "published_at": "2026-05-03T00:00:00Z"},
        ]
        rel, _ = g.pick_lab_release(releases, 4)
        assert rel["tag_name"] == "lab4"


class TestLateBracket:
    def test_brackets(self):
        assert g.late_bracket(-2.0) == "ontime"
        assert g.late_bracket(0) == "ontime"
        assert g.late_bracket(0.5) == "-10%"
        assert g.late_bracket(24) == "-10%"
        assert g.late_bracket(24.1) == "-20%"
        assert g.late_bracket(48) == "-20%"
        assert g.late_bracket(48.1) == "REJECTED"
