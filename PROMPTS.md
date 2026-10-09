# Prompts used in SyllaSync

This file is the "AI Prompt(s) Used During Development" submission item. It has two parts: the prompts the **app** sends to Gemini, and the prompts used while **building** the app.

---

## Part 1: Prompts inside the app (Google Gemini API)

### Prompt 1: Syllabus extraction (`core.py → EXTRACTION_PROMPT`)

Sent together with the raw PDF bytes (`mime_type="application/pdf"`). Gemini reads the PDF natively, with no OCR step.

```text
You are an expert academic advisor reading a university course syllabus.
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
```

**Config:** `response_mime_type="application/json"`, `response_schema=Syllabus` (Pydantic model), `temperature=0.1`.

**Prompt-engineering choices and why:**

| Technique | Why |
|---|---|
| Structured output with a Pydantic `response_schema` | Guarantees valid JSON of the same shape every time, so the UI never breaks on a malformed reply. |
| Field `description`s in the schema | Gemini reads them as extra per-field instructions (e.g. "ISO date YYYY-MM-DD, null if TBA"). |
| "Never invent" rule + `null` allowed | Lets the model say "I don't know" instead of hallucinating a date. |
| Explicit week-number rule | Real syllabi often say "Week 13, Thursday". This tells Gemini how to compute the date and to flag it. |
| `warnings` field | Turns the model's uncertainty into something the student sees and can fix. |
| Low temperature (0.1) | Extraction needs consistency, not creativity. |
| Ungraded items excluded | Keeps the calendar from filling up with holidays and readings. |

### Prompt 2: "Ask your syllabus" (`core.py → answer_question`)

```text
You are a helpful study planner. Answer the student's question using ONLY this course data.
If the answer isn't in the data, say so. Be brief and concrete; use dates and percentages.

Today is {today}.

Course data:
{extracted JSON}

Question: {question}
```

Grounding the answer in the already-extracted JSON (instead of re-sending the PDF) is faster and cheaper, and it means the answer reflects any corrections the student made in the edit table.

### Schema (abridged)

```python
class Syllabus(BaseModel):
    course_code: str
    course_title: str
    instructor: Optional[str]
    term: Optional[str]
    grade_categories: list[GradeCategory]   # name, weight_percent, count, drop_lowest
    events: list[CourseEvent]               # title, event_type, date, time, category, weight_percent, notes
    grading_scale: Optional[str]
    warnings: list[str]
```

---

## Part 2: Prompts used while building

<!-- Rayha: log your real development prompts here, in order, with the tool you used. -->

| # | Tool | Prompt (summary or verbatim) | What it produced |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
