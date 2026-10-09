# Devpost submission: copy each section into its field

## Project name
SyllaSync

## Elevator pitch (under 200 characters)
Drop in any syllabus PDF and Gemini turns it into a synced calendar, a weighted grade tracker, and a "what do I need on the final?" calculator in seconds.

## About the project (paste everything between the lines)

---

## Inspiration
Every semester starts the same way: five syllabi in five different formats, and an hour of copying due dates into a calendar by hand. Grade weights get lost too, so by finals week most students have no idea what score they actually need. I wanted a tool that reads a syllabus the way a student does and does the busywork for them.

## What it does
- **Upload a syllabus PDF.** Gemini reads it directly, including tables and messy layouts.
- **Extracts every graded item** (exams, quizzes, homework, labs, projects) with dates, times, and grade weights.
- **Flags problems:** weights that don't add to 100%, "TBA" dates, and dates it had to compute (like "Thursday of Week 13").
- **Review & edit:** every item is editable, because AI can make mistakes and the student should have the final say.
- **Exports a `.ics` calendar** with reminders that imports into Google, Apple, or Outlook Calendar.
- **Crunch weeks:** highlights the weeks with the most grade weight due.
- **Grade calculator:** enter your scores so far and see the average you need on the remaining work.
- **Ask your syllabus:** questions like "What's due in the next two weeks?" are answered by Gemini using only the extracted data.

## How I built it
- **Google Gemini API** is the core. The PDF goes to Gemini as raw bytes, and I use **structured output** with a Pydantic `response_schema`, so Gemini always returns JSON of the exact shape the app expects. The field descriptions in the schema double as instructions.
- **Python + Streamlit** for the web app, which let me build a working UI quickly as a solo builder.
- **Plain Python for the math.** The LLM handles the fuzzy part (reading documents); deterministic code handles calendar generation and grade arithmetic, so the numbers are exact:

$$s_{\text{needed}} = \frac{G_{\text{target}} - \sum_{\text{graded}} w_i s_i}{\sum_{\text{remaining}} w_j}$$

- **Unit tests** cover everything that doesn't call the API (calendar format, grade math, validation).
- Deployed on **Streamlit Community Cloud**. All prompts are documented in `PROMPTS.md`.

## Challenges I ran into
- **Syllabi don't agree on how to write dates.** "Oct 14," "Week 7 Thursday," and "TBA" all show up. I wrote explicit rules into the prompt: compute week-based dates from the term start and flag them, and return `null` instead of guessing when a date is unknown.
- **Stopping the model from inventing things.** Allowing `null` fields and adding a `warnings` list gave Gemini a way to express uncertainty instead of hallucinating.
- **Double-counted weights.** My first "crunch weeks" calculation counted the Final Project's 10% twice because it had two deliverables (report and presentation). I fixed it by splitting a category's weight across its items, and added a test.
- **Trusting AI output.** I added a validation layer and an editable review table so mistakes get caught before they land in someone's calendar.

## What I learned
- Structured output with a schema is what makes LLM results reliable enough to build a product on.
- Splitting the work between the LLM (reading messy input) and regular code (math, file formats) gives better results than asking the model to do everything.
- Scoping a project down to something finishable in a day.

## What's next
- Direct Google Calendar sync instead of a file download
- Multi-course dashboard showing the whole semester's crunch weeks
- Canvas integration to pull real scores into the grade calculator

---

## Built with (add each as a tag)
python, streamlit, google-gemini, gemini-api, google-ai-studio, pydantic, pandas, icalendar, graphviz, streamlit-community-cloud

## "Try it out" links
1. Live app: https://<your-app-name>.streamlit.app
2. Source code: https://github.com/<your-username>/syllasync

## Image gallery (upload in this order)
1. assets/cover.png
2. Screenshot: upload screen
3. Screenshot: timeline + crunch weeks
4. Screenshot: grade calculator
5. assets/architecture.png
