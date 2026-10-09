"""SyllaSync: turn any syllabus PDF into a calendar, grade tracker, and study planner.

Run locally:   streamlit run app.py
"""

import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from core import (
    DEFAULT_MODEL,
    CourseEvent,
    GradeCategory,
    Syllabus,
    answer_question,
    crunch_weeks,
    dated_events,
    extract_syllabus,
    local_warnings,
    needed_score,
    to_ics,
    weight_total,
)

HERE = Path(__file__).parent

st.set_page_config(page_title="SyllaSync", page_icon="📅", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 2rem; max-width: 1150px;}
.hero h1 {font-size: 2.6rem; margin-bottom: 0;}
.hero p {font-size: 1.1rem; opacity: .75; margin-top: .25rem;}
.pill {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.8rem;
       font-weight:600; margin-right:6px;}
.exam {background:#fde2e1; color:#a1201b;}
.quiz {background:#fff1cc; color:#7a5300;}
.assignment {background:#dcecff; color:#0b4f9c;}
.project {background:#e6defd; color:#4b2aa6;}
.lab {background:#d9f5e5; color:#0f6b3a;}
.presentation {background:#ffe0f0; color:#9a1b5c;}
.other {background:#ececec; color:#444;}
.event-row {padding:.55rem .2rem; border-bottom:1px solid rgba(128,128,128,.18);}
.muted {opacity:.65; font-size:.88rem;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    secret_key = ""
    try:
        secret_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass
    secret_key = secret_key or os.environ.get("GEMINI_API_KEY", "")
    if secret_key:
        st.success("Gemini API key loaded")
        api_key = secret_key
    else:
        api_key = st.text_input("Gemini API key", type="password", help="Free at aistudio.google.com")
    model = st.text_input("Model", value=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
    term_hint = st.text_input("Term (optional)", placeholder="e.g. Fall 2026, starts Aug 24")
    reminder_days = st.slider("Calendar reminder (days before)", 0, 7, 2)
    st.divider()
    st.caption("Your syllabus is sent to the Gemini API for extraction and is not stored by SyllaSync.")

# ---------------------------------------------------------------- hero
st.markdown(
    '<div class="hero"><h1>📅 SyllaSync</h1>'
    "<p>Drop in a syllabus. Get every deadline in your calendar and know exactly what you need on the final.</p></div>",
    unsafe_allow_html=True,
)

col_up, col_demo = st.columns([3, 1])
with col_up:
    uploaded = st.file_uploader("Upload a syllabus (PDF)", type=["pdf"])
with col_demo:
    st.write("")
    st.write("")
    demo = st.button("Try the demo syllabus", use_container_width=True)

if demo:
    data = json.loads((HERE / "assets" / "sample_extraction.json").read_text())
    st.session_state.syllabus = Syllabus.model_validate(data)
    st.session_state.source = "demo"

if uploaded is not None and st.button("✨ Extract with Gemini", type="primary"):
    if not api_key:
        st.error("Add a Gemini API key in the sidebar first.")
    else:
        with st.spinner("Gemini is reading your syllabus..."):
            try:
                st.session_state.syllabus = extract_syllabus(uploaded.getvalue(), api_key, model, term_hint or None)
                st.session_state.source = uploaded.name
            except Exception as exc:  # show the real error; it's usually a key or model-name problem
                st.error(f"Extraction failed: {exc}")

syl: Syllabus | None = st.session_state.get("syllabus")
if syl is None:
    st.info("Upload a PDF and click **Extract with Gemini**, or try the demo syllabus.")
    st.stop()

if st.session_state.get("source") == "demo":
    st.caption("Demo mode: showing a pre-built example result for `assets/sample_syllabus.pdf`. Upload a PDF to run Gemini live.")

# ---------------------------------------------------------------- summary
st.subheader(f"{syl.course_code} · {syl.course_title}".strip(" ·"))
meta = " · ".join(x for x in [syl.instructor, syl.term] if x)
if meta:
    st.markdown(f'<span class="muted">{meta}</span>', unsafe_allow_html=True)

events_dated = dated_events(syl)
upcoming = [e for e in events_dated if date.fromisoformat(e.date) >= date.today()]
m1, m2, m3, m4 = st.columns(4)
m1.metric("Graded items", len(syl.events))
m2.metric("With dates", len(events_dated))
m3.metric("Weights total", f"{weight_total(syl)}%")
m4.metric("Next due", upcoming[0].title if upcoming else "—")

all_warnings = list(dict.fromkeys(syl.warnings + local_warnings(syl)))
if all_warnings:
    with st.expander(f"⚠️ {len(all_warnings)} thing(s) to double-check", expanded=True):
        for w in all_warnings:
            st.markdown(f"- {w}")

tab_tl, tab_edit, tab_grade, tab_ask, tab_raw = st.tabs(
    ["🗓️ Timeline", "✏️ Review & edit", "🎯 Grade calculator", "💬 Ask your syllabus", "{ } JSON"]
)

# ---------------------------------------------------------------- timeline
with tab_tl:
    left, right = st.columns([2, 1])
    with left:
        if not events_dated:
            st.write("No dated items found.")
        for e in events_dated:
            d = date.fromisoformat(e.date)
            past = d < date.today()
            weight = f" · {e.weight_percent}%" if e.weight_percent is not None else ""
            when = d.strftime("%a %b %d") + (f" · {e.time}" if e.time else "")
            st.markdown(
                f'<div class="event-row" style="opacity:{0.45 if past else 1}">'
                f'<span class="pill {e.event_type}">{e.event_type}</span>'
                f"<b>{e.title}</b><span class='muted'>{weight}</span><br>"
                f'<span class="muted">{when}{" · " + e.notes if e.notes else ""}</span></div>',
                unsafe_allow_html=True,
            )
    with right:
        st.markdown("**🔥 Crunch weeks**")
        st.caption("Weeks with the most grade weight due")
        for week, w, titles in crunch_weeks(syl):
            st.markdown(f"**Week of {date.fromisoformat(week).strftime('%b %d')}** — {w}%")
            st.caption(", ".join(titles))
        st.divider()
        fname = f"{(syl.course_code or 'course').replace(' ', '_')}_deadlines.ics"
        st.download_button(
            "⬇️ Download calendar (.ics)",
            to_ics(syl, reminder_days),
            file_name=fname,
            mime="text/calendar",
            type="primary",
            use_container_width=True,
        )
        st.caption("Opens in Google Calendar, Apple Calendar, or Outlook.")

# ---------------------------------------------------------------- edit
with tab_edit:
    st.caption("AI can make mistakes. Fix anything here and the timeline, calendar, and calculator update.")
    df = pd.DataFrame([e.model_dump() for e in syl.events])
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "event_type": st.column_config.SelectboxColumn(
                options=["exam", "quiz", "assignment", "project", "lab", "presentation", "other"]
            ),
        },
        key="editor",
    )
    cats = pd.DataFrame([c.model_dump() for c in syl.grade_categories])
    edited_cats = st.data_editor(cats, num_rows="dynamic", use_container_width=True, key="cat_editor")
    if st.button("Apply changes"):
        rows = edited.where(pd.notna(edited), None).to_dict("records")
        crow = edited_cats.where(pd.notna(edited_cats), None).to_dict("records")
        st.session_state.syllabus = syl.model_copy(
            update={
                "events": [CourseEvent.model_validate(r) for r in rows if r.get("title")],
                "grade_categories": [GradeCategory.model_validate(r) for r in crow if r.get("name")],
            }
        )
        st.rerun()

# ---------------------------------------------------------------- grade calc
with tab_grade:
    if not syl.grade_categories:
        st.write("No grade breakdown found in this syllabus.")
    else:
        target = st.slider("Target final grade", 50, 100, 90)
        st.caption("Enter your average in each category so far. Leave blank if nothing is graded yet.")
        scores = {}
        cols = st.columns(2)
        for i, c in enumerate(syl.grade_categories):
            with cols[i % 2]:
                raw = st.text_input(f"{c.name} ({c.weight_percent}%)", key=f"score_{c.name}", placeholder="e.g. 87")
                try:
                    scores[c.name] = float(raw) if raw.strip() else None
                except ValueError:
                    st.warning("Enter a number")
                    scores[c.name] = None
        r = needed_score(syl.grade_categories, scores, target)
        st.divider()
        if r["status"] == "done":
            st.success(f"Everything is graded. Final grade: **{r['final']}%**")
        elif r["status"] == "impossible":
            st.error(
                f"You'd need **{r['needed']}%** on the remaining {r['remaining_weight']}% of the grade, "
                f"which is above 100%. Try a lower target or check for extra credit."
            )
        elif r["status"] == "locked":
            st.success(f"You've already locked in {target}%. Nice.")
        else:
            st.metric(
                f"Average needed on the remaining {r['remaining_weight']}%",
                f"{r['needed']}%",
                help="(target − points earned) ÷ remaining weight",
            )
            if r["current_avg"] is not None:
                st.caption(f"Your current average on graded work: {r['current_avg']}%")

# ---------------------------------------------------------------- ask
with tab_ask:
    st.caption("Ask anything about this course. Gemini answers using only the extracted data.")
    examples = ["What's due in the next two weeks?", "Which week should I start studying early for?", "How much is the final worth?"]
    ex = st.radio("Try:", examples, horizontal=True, index=None)
    q = st.text_input("Your question", value=ex or "")
    if st.button("Ask Gemini") and q:
        if not api_key:
            st.error("Add a Gemini API key in the sidebar first.")
        else:
            with st.spinner("Thinking..."):
                try:
                    st.markdown(answer_question(syl, q, api_key, model))
                except Exception as exc:
                    st.error(f"Gemini error: {exc}")

# ---------------------------------------------------------------- raw
with tab_raw:
    st.caption("The structured output Gemini returned, validated against the schema in core.py.")
    st.json(syl.model_dump())
