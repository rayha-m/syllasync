"""SyllaSync core logic: schema, Gemini extraction, calendar export, grade math.

Kept separate from the Streamlit UI so it can be unit-tested without a browser
or an API key.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# 1. The schema Gemini must fill in. Field descriptions are part of the prompt:
#    Gemini reads them when deciding what to put in each field.
# --------------------------------------------------------------------------

EventType = Literal["exam", "quiz", "assignment", "project", "lab", "presentation", "other"]


class GradeCategory(BaseModel):
    name: str = Field(description="Category name exactly as the syllabus words it, e.g. 'Midterm Exams'.")
    weight_percent: float = Field(description="Share of the final grade, 0-100. Use the syllabus value.")
    count: Optional[int] = Field(
        default=None,
        description="How many graded items are in this category, if the syllabus says (e.g. 10 quizzes).",
    )
    drop_lowest: Optional[int] = Field(
        default=None, description="Number of lowest scores dropped, if the syllabus says so."
    )


class CourseEvent(BaseModel):
    title: str = Field(description="Short title, e.g. 'Midterm 1' or 'Homework 3'.")
    event_type: EventType
    date: Optional[str] = Field(
        default=None,
        description="ISO date YYYY-MM-DD. Null if the syllabus gives no resolvable date (e.g. 'TBA').",
    )
    time: Optional[str] = Field(default=None, description="24-hour HH:MM if a specific time is given, else null.")
    category: Optional[str] = Field(
        default=None, description="Name of the GradeCategory this item counts toward, matching it exactly."
    )
    weight_percent: Optional[float] = Field(
        default=None,
        description="This single item's share of the final grade if stated or clearly derivable, else null.",
    )
    notes: Optional[str] = Field(
        default=None, description="Anything ambiguous or worth flagging, e.g. 'date given as Week 7'."
    )


class Syllabus(BaseModel):
    course_code: str = Field(description="e.g. 'CSCE 121'. Empty string if not found.")
    course_title: str
    instructor: Optional[str] = None
    term: Optional[str] = Field(default=None, description="e.g. 'Fall 2026'.")
    grade_categories: list[GradeCategory]
    events: list[CourseEvent]
    grading_scale: Optional[str] = Field(
        default=None, description="Letter-grade cutoffs as written, e.g. 'A 90-100, B 80-89...'."
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Problems a student should double-check: weights not summing to 100, TBA dates, conflicts.",
    )


# --------------------------------------------------------------------------
# 2. The extraction prompt. This is the main piece of prompt engineering.
# --------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are an expert academic advisor reading a university course syllabus.
Extract every graded deliverable and the grading breakdown into the JSON schema provided.

Rules:
1. Only use information that appears in the document. Never invent dates, weights, or items.
2. Dates: output YYYY-MM-DD. The academic term is {term_hint}.
   - If the syllabus gives a weekday plus a week number (e.g. "Week 7, Thursday") and the
     term start date is stated, compute the date. Add a note saying it was computed.
   - If a date is "TBA", missing, or impossible to resolve, set date to null and explain in notes.
3. Create one event per graded item. If the syllabus says "Homework due every Friday" and
   lists them, create each one. If it only says "weekly homework" with no list, create a
   single event titled "Weekly homework (recurring)" with a null date and a note.
4. Grade categories: copy weights exactly. If they do not sum to 100, still copy them and
   add a warning stating the actual total.
5. Match each event's category to a grade_categories name exactly.
6. If the per-item weight is stated or clearly derivable (category weight / count, no drops),
   fill weight_percent. Otherwise leave it null.
7. Include final exams, projects, labs, presentations and quizzes. Exclude ungraded readings,
   holidays, and office hours.
8. Put anything a student should double-check into warnings.
"""


def build_prompt(term_hint: str | None) -> str:
    return EXTRACTION_PROMPT.format(term_hint=term_hint or "unknown; infer it from the document")


DEFAULT_MODEL = "gemini-flash-latest"


def extract_syllabus(pdf_bytes: bytes, api_key: str, model: str = DEFAULT_MODEL, term_hint: str | None = None) -> Syllabus:
    """Send the PDF straight to Gemini and get back a validated Syllabus object.

    Gemini reads PDFs natively (text, tables and layout), so there is no OCR or
    text-extraction step. `response_schema` forces the output to match our
    Pydantic model, which is what makes the result safe to build a UI on.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            build_prompt(term_hint),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Syllabus,
            temperature=0.1,  # extraction, not creativity
        ),
    )
    if getattr(response, "parsed", None) is not None:
        return response.parsed
    return Syllabus.model_validate(json.loads(response.text))


def answer_question(syllabus: Syllabus, question: str, api_key: str, model: str = DEFAULT_MODEL) -> str:
    """Second Gemini call: answer free-form questions grounded in the extracted data."""
    from google import genai

    client = genai.Client(api_key=api_key)
    prompt = (
        "You are a helpful study planner. Answer the student's question using ONLY this course data. "
        "If the answer isn't in the data, say so. Be brief and concrete; use dates and percentages.\n\n"
        f"Today is {date.today().isoformat()}.\n\nCourse data:\n{syllabus.model_dump_json(indent=1)}\n\n"
        f"Question: {question}"
    )
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text


# --------------------------------------------------------------------------
# 3. Validation helpers (no AI): catch problems Gemini might miss.
# --------------------------------------------------------------------------

def weight_total(s: Syllabus) -> float:
    return round(sum(c.weight_percent for c in s.grade_categories), 2)


def local_warnings(s: Syllabus) -> list[str]:
    out = []
    total = weight_total(s)
    if s.grade_categories and abs(total - 100) > 0.5:
        out.append(f"Grade weights add up to {total}%, not 100%.")
    names = {c.name for c in s.grade_categories}
    for e in s.events:
        if e.category and e.category not in names:
            out.append(f"'{e.title}' is in category '{e.category}', which isn't in the grade breakdown.")
        if e.date:
            try:
                date.fromisoformat(e.date)
            except ValueError:
                out.append(f"'{e.title}' has an unreadable date: {e.date}.")
    undated = [e.title for e in s.events if not e.date]
    if undated:
        out.append(f"{len(undated)} item(s) have no date yet: {', '.join(undated[:5])}{'...' if len(undated) > 5 else ''}.")
    return out


def dated_events(s: Syllabus) -> list[CourseEvent]:
    good = []
    for e in s.events:
        try:
            if e.date:
                date.fromisoformat(e.date)
                good.append(e)
        except ValueError:
            pass
    return sorted(good, key=lambda e: (e.date, e.time or ""))


def crunch_weeks(s: Syllabus, top: int = 3) -> list[tuple[str, float, list[str]]]:
    """Weeks with the most grade weight due. Returns (week_start, weight, titles)."""
    weights = {c.name: c.weight_percent for c in s.grade_categories}
    per_cat = {}
    for e in s.events:
        if e.category:
            per_cat[e.category] = per_cat.get(e.category, 0) + 1
    buckets: dict[date, list] = {}
    for e in dated_events(s):
        d = date.fromisoformat(e.date)
        monday = d - timedelta(days=d.weekday())
        w = e.weight_percent
        if w is None and e.category in weights:
            # Split the category's weight evenly across its items (estimate).
            w = weights[e.category] / per_cat[e.category]
        buckets.setdefault(monday, []).append((w or 0, e.title))
    ranked = sorted(buckets.items(), key=lambda kv: -sum(x[0] for x in kv[1]))[:top]
    return [(m.isoformat(), round(sum(x[0] for x in items), 1), [t for _, t in items]) for m, items in ranked]


# --------------------------------------------------------------------------
# 4. Calendar export (.ics), written by hand: the format is simple and this
#    avoids another dependency.
# --------------------------------------------------------------------------

def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def to_ics(s: Syllabus, reminder_days: int = 2) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"{s.course_code} " if s.course_code else ""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SyllaSync//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_esc((s.course_code or s.course_title) + ' deadlines')}",
    ]
    for e in dated_events(s):
        d = date.fromisoformat(e.date)
        lines += ["BEGIN:VEVENT", f"UID:{uuid.uuid4()}@syllasync", f"DTSTAMP:{stamp}"]
        if e.time:
            try:
                h, m = (int(x) for x in e.time.split(":")[:2])
                start = datetime(d.year, d.month, d.day, h, m)
                lines += [
                    f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
                    f"DTEND:{(start + timedelta(hours=1)).strftime('%Y%m%dT%H%M%S')}",
                ]
            except ValueError:
                e = e.model_copy(update={"time": None})
        if not e.time:
            lines += [
                f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{(d + timedelta(days=1)).strftime('%Y%m%d')}",
            ]
        desc = [f"Type: {e.event_type}"]
        if e.category:
            desc.append(f"Category: {e.category}")
        if e.weight_percent is not None:
            desc.append(f"Worth {e.weight_percent}% of final grade")
        if e.notes:
            desc.append(e.notes)
        lines += [
            f"SUMMARY:{_esc(prefix + e.title)}",
            f"DESCRIPTION:{_esc(chr(10).join(desc))}",
        ]
        if reminder_days > 0:
            lines += [
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{_esc(prefix + e.title)} coming up",
                f"TRIGGER:-P{reminder_days}D",
                "END:VALARM",
            ]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# --------------------------------------------------------------------------
# 5. Grade math (no AI): deterministic, so the numbers are trustworthy.
# --------------------------------------------------------------------------

def needed_score(categories: list[GradeCategory], scores: dict[str, Optional[float]], target: float) -> dict:
    """Given category averages entered so far (None = not graded yet), work out
    the average needed on everything remaining to reach `target`.

    current = sum(w_i * s_i) over graded categories
    needed  = (target - current) / sum(w_j) over ungraded categories
    """
    earned = 0.0
    graded_w = 0.0
    remaining_w = 0.0
    for c in categories:
        s = scores.get(c.name)
        if s is None:
            remaining_w += c.weight_percent
        else:
            earned += c.weight_percent * s / 100
            graded_w += c.weight_percent
    current_avg = (earned / graded_w * 100) if graded_w else None
    if remaining_w == 0:
        return {"current_avg": current_avg, "final": round(earned, 2), "needed": None, "status": "done"}
    needed = (target - earned) / remaining_w * 100
    status = "impossible" if needed > 100 else "locked" if needed <= 0 else "ok"
    return {
        "current_avg": None if current_avg is None else round(current_avg, 2),
        "earned_points": round(earned, 2),
        "remaining_weight": round(remaining_w, 2),
        "needed": round(needed, 2),
        "status": status,
    }
