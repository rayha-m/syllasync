"""Run with:  python -m pytest -q   (or just: python tests/test_core.py)"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import (  # noqa: E402
    GradeCategory,
    Syllabus,
    build_prompt,
    crunch_weeks,
    dated_events,
    local_warnings,
    needed_score,
    to_ics,
    weight_total,
)

SAMPLE = Syllabus.model_validate(json.loads((ROOT / "assets" / "sample_extraction.json").read_text()))


def test_sample_weights_sum_to_100():
    assert weight_total(SAMPLE) == 100


def test_undated_items_flagged_and_excluded():
    assert any("no date" in w for w in local_warnings(SAMPLE))
    assert all(e.date for e in dated_events(SAMPLE))
    assert len(dated_events(SAMPLE)) == len(SAMPLE.events) - 1  # Quiz 5 is TBA


def test_bad_weights_warn():
    bad = SAMPLE.model_copy(update={"grade_categories": SAMPLE.grade_categories[:-1]})
    assert any("85" in w for w in local_warnings(bad))


def test_ics_is_valid_shape():
    ics = to_ics(SAMPLE)
    assert ics.startswith("BEGIN:VCALENDAR") and ics.rstrip().endswith("END:VCALENDAR")
    assert ics.count("BEGIN:VEVENT") == len(dated_events(SAMPLE))
    assert "DTSTART:20260929T190000" in ics  # Midterm 1 at 7 PM
    assert "DTSTART:20260904T235900" in ics  # HW 1 due 11:59 PM
    assert "DTSTART;VALUE=DATE:20260909" in ics  # Quiz 1 has no time -> all-day event
    assert "TRIGGER:-P2D" in ics
    assert "\r\n" in ics


def test_needed_score_math():
    cats = [GradeCategory(name="A", weight_percent=50), GradeCategory(name="B", weight_percent=50)]
    r = needed_score(cats, {"A": 80, "B": None}, target=90)
    assert r["needed"] == 100.0 and r["status"] == "ok"
    r = needed_score(cats, {"A": 70, "B": None}, target=90)
    assert r["status"] == "impossible"
    r = needed_score(cats, {"A": 100, "B": None}, target=40)
    assert r["status"] == "locked"
    r = needed_score(cats, {"A": 90, "B": 80}, target=90)
    assert r["status"] == "done" and r["final"] == 85


def test_crunch_weeks_finds_midterm_week():
    weeks = crunch_weeks(SAMPLE)
    assert weeks[0][0] in ("2026-09-28", "2026-11-02", "2026-12-14")
    assert weeks[0][1] >= 15


def test_prompt_includes_term():
    assert "Fall 2026" in build_prompt("Fall 2026")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
