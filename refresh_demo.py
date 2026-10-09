"""Re-run Gemini on the sample syllabus and save the real output as the demo result.

Usage:  GEMINI_API_KEY=your_key python refresh_demo.py
"""

import json
import os
from pathlib import Path

from core import extract_syllabus

here = Path(__file__).parent
pdf = (here / "assets" / "sample_syllabus.pdf").read_bytes()
result = extract_syllabus(pdf, os.environ["GEMINI_API_KEY"], term_hint="Fall 2026, classes begin Aug 24, 2026")
(here / "assets" / "sample_extraction.json").write_text(json.dumps(result.model_dump(), indent=2))
print(f"Saved {len(result.events)} events from Gemini to assets/sample_extraction.json")
