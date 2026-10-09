# Finishing SyllaSync: your checklist

Deadline: **Fri Oct 9, 1:45 AM CDT.** Submit by 11 PM Thursday to leave a buffer. Delete this file before pushing if you like.

## 1. Get a Gemini API key (5 min)
1. Go to https://aistudio.google.com/apikey and sign in with a Google account.
2. Click **Create API key** and copy it. Treat it like a password: never commit it to GitHub.

## 2. Run it on your computer (10 min)
Open a terminal in the unzipped `syllasync` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GEMINI_API_KEY=paste_key_here # Windows (cmd): set GEMINI_API_KEY=paste_key_here
streamlit run app.py
```

A browser tab opens. Upload `assets/sample_syllabus.pdf`, click **Extract with Gemini**, and check the results.

- **Error mentioning the model name?** Open the sidebar and change *Model* to a current one listed at https://ai.google.dev/gemini-api/docs/models (for example a "flash" model).
- Then try one of your real syllabi.

## 3. Replace the demo result with real Gemini output (2 min)
```bash
python refresh_demo.py
```
This makes the "Try the demo syllabus" button show a genuine Gemini result.

## 4. Push to GitHub (10 min)
1. At https://github.com/new, create a public repo named `syllasync`. Don't add a README (you have one).
2. In the terminal:
```bash
git init
git add .
git commit -m "SyllaSync: syllabus to semester plan with Gemini"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/syllasync.git
git push -u origin main
```
`.gitignore` already keeps `secrets.toml` out of the repo.

## 5. Deploy (10 min)
1. Go to https://share.streamlit.io and sign in with GitHub.
2. **Create app** → pick the `syllasync` repo, branch `main`, file `app.py`.
3. **Advanced settings → Secrets**, paste: `GEMINI_API_KEY = "your_key"`
4. Deploy. Copy the `.streamlit.app` URL.

## 6. Fill in the placeholders (10 min)
- `PROMPTS.md` Part 2: the AI tools and prompts you used while building.
- `README.md`: your GitHub username in the clone URL.
- Last slide of the deck: your app URL and GitHub URL.
- `DEVPOST.md`: the two "Try it out" links.

## 7. Screenshots + video (30 min)
- Screenshots of the upload screen, timeline, and grade calculator for the Devpost gallery.
- Record a 2–3 min demo (Loom, or QuickTime on Mac / Xbox Game Bar on Windows):
  problem → upload → warnings → timeline & crunch weeks → download calendar → grade calculator → ask a question → architecture slide.
- Upload to YouTube as **Unlisted**.

## 8. Submit
- Copy each section of `DEVPOST.md` into its Devpost field.
- Gallery: `assets/cover.png` first, then screenshots, then `assets/architecture.png`.
- "Upload a File": the `judges_package.zip` (after adding the slides PDF; see below).
- Export the slides as PDF (Share › Export on the deck) and add it to the zip.
