# MediAI: AI-Powered Medical Assistant

MediAI explains medical information in simple language, in **English, Hindi, Telugu and Tamil**.
It was built for the Indian Servers Internship Innovation Challenge.

> **Educational use only.** MediAI is not a doctor. It never diagnoses, never gives medicine doses, and its AI
> answers are not clinically validated. **In an emergency call 112.**

| Tool | What it does |
|------|--------------|
| Report Explainer | Upload a photo, PDF or text of a lab report (or paste the text). Every test is explained in plain words. |
| Symptom Checker | Click a body area, choose symptoms, add details. Get general guidance, never a diagnosis. |
| Medicine Info | Search a medicine. Uses an official FDA drug label when one exists, and says clearly when it cannot verify. |
| Health Summary | Turns what you type into a structured summary. Copy or download it. |
| Emergency warnings | Fixed safety rules (not AI) show a red 112 alert for serious warning signs, in all 4 languages. |

---

## 1. How it works (simple version)

```
  Your browser                     MediAI server (Flask, Python)                  Outside services
 ┌────────────────┐   request   ┌──────────────────────────────────┐
 │ HTML + CSS + JS│ ──────────► │ 1. check the input (size, type)  │
 │ (frontend/)    │             │ 2. EMERGENCY RULES run first     │ ──(only if no red flag)──► Google Gemini API
 │                │ ◄────────── │ 3. read the file (OCR / PDF)     │ ──────────────────────────► openFDA (medicine labels)
 └────────────────┘   answer    │ 4. build the answer              │
                                └──────────────────────────────────┘
        Your API key lives ONLY here, on the server, in an environment variable.
```

**Why Flask, and why one server?** Flask is the simplest Python web framework, and it can serve the website files
*and* the API from the same program. That means: one command to run, no CORS problems, nothing to connect, and the
same code runs on your PC, in Colab and on a hosting site. A separate frontend server (React etc.) would add
complexity without any benefit for a project this size.

**Safety design in one paragraph.** When a symptom text arrives, rule-based red-flag checks run **first**. If they
find a warning sign (chest pain, trouble breathing, stroke signs, heavy bleeding, thoughts of self-harm, ...), the
server answers *immediately* with the emergency banner and **does not call the AI at all**. Otherwise the AI answers,
and it can raise the emergency flag too. While you type, the page also checks your text every half second and shows
a compact sticky red banner, so a warning is never missed.

---

## 2. Project structure

```
MediAI/
├── app.py                    Starts the server
├── requirements.txt          Python packages
├── .env.example              Template for your secret settings (copy to .env)
├── Dockerfile                Used for online hosting (also installs OCR)
├── MediAI_Colab.ipynb        Ready-made Google Colab notebook
├── README.md                 This file
├── backend/
│   ├── __init__.py           create_app(): builds the Flask app
│   ├── config.py             Settings read from environment variables
│   ├── routes/               The API addresses (one file per feature)
│   │   ├── common_routes.py      /api/health, /api/safety/check
│   │   ├── report_routes.py      /api/report/analyze
│   │   ├── symptom_routes.py     /api/symptoms/analyze
│   │   ├── medicine_routes.py    /api/medicines/search
│   │   └── summary_routes.py     /api/summary/generate
│   ├── services/             The "brains"
│   │   ├── safety_service.py     Emergency red-flag rules (no AI)
│   │   ├── gemini_service.py     All Gemini calls, timeouts, fallbacks, friendly errors
│   │   ├── prompts.py            The instructions given to Gemini
│   │   ├── normalize.py          Forces AI answers into a safe, fixed shape
│   │   ├── ocr_service.py        Text from images (Tesseract / Gemini vision), PDFs, TXT
│   │   └── medicine_service.py   openFDA label lookup
│   └── utils/
│       ├── validators.py         Checks every input
│       ├── file_utils.py         Safe file reading (type, size, real content)
│       ├── rate_limit.py         Stops one visitor from using up your quota
│       ├── errors.py             Clean JSON errors
│       └── messages.py           Fixed disclaimers/emergency text in 4 languages
├── frontend/
│   ├── index.html            Landing page
│   ├── dashboard.html        Main dashboard
│   ├── report.html, symptoms.html, medicines.html, summary.html
│   ├── about.html, disclaimer.html
│   ├── css/style.css
│   └── js/
│       ├── i18n.js           All translations (4 languages)
│       ├── app.js            Navigation, language selector, helpers
│       └── report.js, symptoms.js, medicines.js, summary.js
├── sample_data/              Fictional sample report (.txt, .png, .pdf) for testing
├── tests/                    43 automatic tests (no internet or API key needed)
└── uploads/.gitkeep          Unused on purpose: uploaded files are never saved
```

---

## 3. Get your free Gemini API key

1. Open <https://aistudio.google.com/apikey> and sign in with a Google account.
2. Click **Create API key**, then copy it (it looks like `AIza...`).
3. Keep it secret. Never post it on GitHub, in screenshots, or in code.

**Model names change.** Google retires Gemini models regularly (Gemini 2.5 models are being replaced by newer ones
around December 2026). MediAI reads the model from `GEMINI_MODEL` and automatically tries fallback models, so a
retired name will not break it. If you ever see *"None of the configured Gemini models is available"*, open
<https://ai.google.dev/gemini-api/docs/models>, copy a current Flash or Flash-Lite model name, and put it in `.env`.

**Privacy warning about free keys.** Under Google's terms, content sent through *free-tier* Gemini keys may be used
to improve Google's products. For demos use the fictional files in `sample_data/`, **not** real medical records.

---

## 4. Run it on your Windows PC (VS Code + PowerShell)

**One-time setup**

1. Install **Python 3.10 or newer** from <https://www.python.org/downloads/>. On the first installer screen tick
   **"Add python.exe to PATH"**.
2. Install **VS Code** from <https://code.visualstudio.com/> and its **Python** extension.
3. Unzip `MediAI.zip`, then in VS Code choose **File > Open Folder** and open the `MediAI` folder.
4. Open the terminal: **Terminal > New Terminal** (it should say PowerShell).

**Run these commands one by one** (lines starting with `#` are comments, do not type them):

```powershell
python --version                        # should print Python 3.10 or higher
python -m venv venv                     # creates a private box for MediAI's packages
.\venv\Scripts\Activate.ps1             # turns the box on; your prompt now starts with (venv)
python -m pip install --upgrade pip
pip install -r requirements.txt         # installs everything (1 to 2 minutes)
Copy-Item .env.example .env             # creates your private settings file
notepad .env                            # opens it: replace paste-your-key-here with your real key, then Save
python app.py                           # starts MediAI
```

Now open **<http://127.0.0.1:5000>** in your browser. Stop the server with `Ctrl + C` in the terminal.
Next time, you only need: `.\venv\Scripts\Activate.ps1` then `python app.py`.

If PowerShell says *"running scripts is disabled"*, run this once and try the activate line again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Quick check: open <http://127.0.0.1:5000/api/health>. You should see `"gemini_key_configured": true`.

**Optional: Tesseract OCR for photos of reports.** Without it MediAI still works: it uses Gemini's vision to read
images. If you want local OCR, install Tesseract from <https://github.com/UB-Mannheim/tesseract/wiki> (tick the
*Hindi*, *Telugu* and *Tamil* language data during setup). MediAI finds the default install folder automatically.
Otherwise add `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` to `.env`.

---

## 5. Run it in Google Colab

Colab cannot show a normal "localhost" website, so the notebook starts the server inside Colab and opens it through
Colab's built-in proxy (Option A), or through a public ngrok link (Option B). The website only works while the
notebook is running.

1. Go to <https://colab.research.google.com> > **File > Upload notebook** > choose `MediAI_Colab.ipynb`.
2. Run the cells **top to bottom**. The notebook explains each one:

| Cell | Purpose |
|------|---------|
| 1 | Checks your key is in **Colab Secrets** (key icon in the left sidebar: name `GEMINI_API_KEY`, switch on *Notebook access*) |
| 2 | Upload `MediAI.zip` and unzip it |
| 3 | `pip install -r requirements.txt` and install Tesseract (optional) |
| 4 | Copies the secret into an environment variable (never printed) |
| 5 | Starts the server in a background thread on port 5000 |
| 6 | Health check |
| 7 | Opens the website in a new tab (`serve_kernel_port_as_window`), or inline (7b) |
| 8 | Optional ngrok public link (needs a free ngrok account and `NGROK_AUTH_TOKEN` secret) |
| 9 | Tests every feature from code (emergency rules, symptoms, report text/image, medicine, summary in Telugu) |
| 10 | Runs the automatic tests |
| 11 | Stops the server |

**Limits of Colab:** the site is only reachable while the notebook runs; it stops after Colab disconnects; Option A
only works for you. For something you can share permanently, deploy it (section 8). If the page opens but buttons
fail in Option A, use Option B.

---

## 6. How to test every feature

Start the server, open the site, and try these. Sample files are in `sample_data/`.

**Landing + navigation.** Open `/`: you see the logo, hero, example card, feature cards, disclaimer and footer.
Click **Get started** to reach the Dashboard. The sidebar links work on every page. On a phone-sized window the
sidebar becomes a menu button.

**Feature 1: Report Explainer** (`report.html`)
1. Drag `sample_data/sample_report.png` into the upload box. A preview appears.
2. Type the question *What does the low hemoglobin mean?* and click **Analyze report**.
3. Expect: a loading spinner, then a summary, one card per test with **High / Low / Normal** badges (Hemoglobin and
   MCV low, Glucose high), medical terms explained, doctor questions, and a collapsible *"Text read from your report"*
   box so you can check the OCR.
4. Repeat with `sample_report.pdf`, `sample_report.txt`, and by pasting text.
5. Try `anything.exe` or a file over 8 MB: you get a clear error and nothing is processed.
6. Switch the language (top right) to Hindi/Telugu/Tamil and analyze again: the explanations come in that language.
   (A report with no printed reference range should show **Not determined**: the AI is told never to guess ranges.)

**Feature 2: Symptom Checker** (`symptoms.html`)
1. Click the **throat** on the body (or the *Throat* chip). It turns teal, and the symptom list appears.
2. Tick *Sore throat*, type a description, choose *Mild*, enter an age, click **Check symptoms**.
3. Expect: a "What you entered" card (green *You provided* badge) and separate AI cards (blue *AI-generated* badge):
   possible explanations (labelled "not a diagnosis"), when to get medical help, warning signs, self-care, questions.
4. Click **Back view** and click the back: the *Back* symptoms appear.
5. **Emergency test:** in the description type `I have crushing chest pain and cannot breathe`. Within about a
   second a **red sticky banner** appears with a **Call 112** button. Click **Check symptoms**: you get the emergency
   banner and **no self-care advice**. Try `सीने में तेज़ दर्द है` (Hindi), `ఛాతీలో నొప్పి` (Telugu) and
   `நெஞ்சு வலி` (Tamil). Then type `no chest pain, just a mild cough`: the banner disappears.
6. Type `I want to die`: you get support text including Tele-MANAS (14416) and 112.

**Feature 3: Medicine Info** (`medicines.html`)
1. Search `Paracetamol`: you should see a green *Based on an official drug label* badge, uses, side effects,
   warnings, interactions, storage, and pharmacist questions. There is never a dose.
2. Search `Dolo 650`: an Indian brand is mapped to its ingredient, then looked up.
3. Search a made-up word such as `Zorbitrex`: you should be asked for more information, not given invented facts.
4. A medicine with no label found shows an amber *AI-generated and not independently verified* badge.

**Feature 4: Health Summary** (`summary.html`)
1. Fill a few fields (for example age 34, history *diabetes since 2019*, medication *Metformin*, allergy
   *penicillin*, symptoms *tiredness for two weeks*) and click **Generate summary**.
2. Expect 7 sections: the first five restate *only what you typed* (*You provided*), the last two are AI suggestions.
3. **Copy** and **Download** (a `.txt` file, including the disclaimer).
4. Tick *Save on this device only*, generate, reload the page: your answers are back. Click **Clear saved data**:
   gone. With the box unticked, nothing is stored anywhere.

**Feature 5: Languages.** Use the selector at the top right. Menus, headings, buttons, disclaimers, emergency
messages and AI answers all change. Your choice is remembered. (Symptom *names* in the checklist stay in English;
you can describe symptoms in your own language in the text box.)

**Feature 6: Emergency detection.** See the symptom tests above. It also runs on the Health Summary's *Symptoms* and
*Recent concerns* boxes, and you can call it directly: `POST /api/safety/check`.

**Automatic tests (no API key needed):**

```powershell
python -m unittest discover -s tests -v
```

---

## 7. Safety and privacy summary

| Requirement | How MediAI handles it |
|-------------|----------------------|
| Disclaimers | Landing page, every tool page, every AI answer, a dedicated page; fixed text in 4 languages |
| No diagnosis | Prompts forbid it; wording is "possible explanations"; urgency levels, never certainty |
| No invented lab values or ranges | Prompt rules; `not_determined` flag when no range is printed; extracted text is shown for checking |
| No medication changes or doses | Forbidden in every prompt; the medicine schema has no dosage field; dosage sections are not even given to the AI |
| Emergencies | Rule-based checks first (12 categories, 4 languages), instant sticky banner, AI skipped, 112 shown |
| User info vs AI text | Green *You provided* vs blue *AI-generated* badges; "What you entered" card |
| Files | Checked by type, size and real content; processed in memory; never saved; images re-encoded (strips GPS metadata) |
| Secrets | API key only in environment variables; `/api/health` only says yes/no |
| Browser safety | All AI/user text is HTML-escaped before display |
| Abuse | Per-visitor rate limit; request size limit; input length limits |
| Storage | Nothing stored on the server. Only your language choice (and, if you opt in, the summary form) stays in *your* browser |

**Known limitations (be honest about these in your demo):** keyword rules cannot catch every phrasing, so they
err on the side of showing the warning (for example "chest pain" always triggers it); AI can misread numbers in
photos (always check the extracted text); medicine labels come from the US FDA database, and Indian brands can
differ; the app has not been clinically validated.

---

## 8. Deploy online (beginner-friendly: Render, free tier)

Render can run the included `Dockerfile`, which also installs Tesseract. (Render's menus and free-tier rules change
over time, so follow what the website shows if it differs slightly.)

1. **Put the project on GitHub.** Create an account at <https://github.com>, create a new *private* repository, then in
   the VS Code terminal:
   ```powershell
   git init
   git add .
   git commit -m "MediAI"
   git branch -M main
   git remote add origin https://github.com/YOUR-NAME/MediAI.git
   git push -u origin main
   ```
   Check on GitHub that `.env` is **not** there (it is listed in `.gitignore`, so it should not be).
2. Create an account at <https://render.com> (sign in with GitHub).
3. Click **New +** > **Web Service** > pick your `MediAI` repository.
4. Set **Language/Runtime** to **Docker**, and the **Instance type** to **Free**.
5. Under **Environment Variables** add `GEMINI_API_KEY` = your key (and optionally `GEMINI_MODEL`).
6. Click **Create Web Service**. The first build takes several minutes. You will get a link like
   `https://mediai-xxxx.onrender.com`. Optionally set the health check path to `/api/health`.

**Things to know:** free web services go to sleep when idle, so the first visit after a break can take about a minute;
anyone with your link can use your Gemini quota (the built-in rate limit is per visitor per minute), so share the link
only for the demo period; uploaded files are never saved, so Render's temporary disk is not a problem. Any host that
runs Docker (Railway, Fly.io, Google Cloud Run) works the same way.

---

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| `python` is not recognized | Reinstall Python and tick *Add python.exe to PATH*, or use `py` instead of `python` |
| *Running scripts is disabled* when activating `venv` | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again |
| `ModuleNotFoundError: No module named 'flask'` (or `google`) | The venv is not active (prompt must start with `(venv)`), or run `pip install -r requirements.txt` |
| *The Gemini API key is missing* | `.env` must be in the `MediAI` folder (next to `app.py`), contain `GEMINI_API_KEY=AIza...` with no quotes or spaces, and you must restart the server. In Colab: re-run cells 4 and 5 |
| *Gemini rejected the API key* | The key is wrong, deleted or restricted. Create a new one at aistudio.google.com/apikey |
| *The free Gemini quota is used up* | Wait a minute (or until tomorrow). Free keys have per-minute and per-day limits |
| *None of the configured Gemini models is available* | Set `GEMINI_MODEL` to a current model name (section 3) |
| *The AI service is busy* | Temporary. Try again in a moment (MediAI already retries once) |
| `Address already in use` / port 5000 busy | Set `PORT=5001` in `.env` and open `http://127.0.0.1:5001`. In Colab, Runtime > Restart session |
| Page looks unstyled or old after an update | Hard refresh: `Ctrl + F5` |
| Hindi/Telugu/Tamil shows empty boxes | Update your browser; Windows 10/11 include the needed fonts. Fonts also load from Google Fonts when online |
| Report image text is wrong | Upload a sharper, well-lit, straight photo, or paste the text. Always read the *Text read from your report* box |
| *This PDF looks scanned* warning | Normal: the AI read the pages visually. Check the extracted text |
| *The file content does not match its type* | The file was renamed (for example a .png that is really something else). Re-export it |
| Tesseract errors | Optional. Remove `TESSERACT_CMD` or set `OCR_ENGINE=gemini` in `.env` |
| *You are sending requests too quickly* | Wait a minute (limit is `RATE_LIMIT_PER_MINUTE`, default 20) |
| Colab: page opens but buttons fail | Use Option B (ngrok), cell 8 |
| Colab: `NotebookAccessError` / secret not found | Left sidebar key icon: the secret name must be exactly `GEMINI_API_KEY`, and *Notebook access* must be on |
| Render build fails | Open the *Logs* tab; make sure the runtime is **Docker** and `Dockerfile` is at the repository root |

---

## 10. Implementation checklist and how to verify each item

| # | Feature | Where | How to verify |
|---|---------|-------|---------------|
| 1 | Landing page (logo, hero, description, feature cards, Get Started, disclaimer, footer) | `index.html` | Open `/` |
| 2 | Dashboard with tool cards, consistent navigation on all pages | `dashboard.html`, `js/app.js` | Click through all 8 pages |
| 3 | Report upload: image, PDF, TXT, paste, preview, optional question | `report.html`, `report.js` | Section 6, Feature 1 |
| 4 | OCR + PDF text extraction (Tesseract, Gemini-vision fallback, scanned PDFs) | `ocr_service.py` | Upload `sample_report.png` and `.pdf` |
| 5 | Plain-language report analysis with High/Low flags from printed ranges only | `prompts.py`, `report.js` | Hemoglobin shows *Low*; a value with no range shows *Not determined* |
| 6 | Interactive body map (front/back, 14 areas, keyboard accessible) | `symptoms.html`, `symptoms.js` | Click or Tab+Enter on body parts |
| 7 | Symptom form: symptoms, description, duration, severity, age, history | `symptoms.html` | Section 6, Feature 2 |
| 8 | Symptom guidance: summary, possibilities, self-care, when to see a doctor, questions | `symptom_routes.py` | Submit a mild case |
| 9 | Medicine lookup with official-label grounding, unverified marking, "need more info" | `medicine_service.py` | Section 6, Feature 3 |
| 10 | Health summary (7 sections, copy, download, opt-in local save) | `summary.html`, `summary.js` | Section 6, Feature 4 |
| 11 | 4 languages for UI, AI answers, disclaimers, summaries | `i18n.js`, `prompts.py`, `messages.py` | Switch language and re-run |
| 12 | Deterministic emergency detection (12 categories, 4 languages, negation-aware), sticky live banner, AI skipped | `safety_service.py` | Section 6, Feature 2 step 5 |
| 13 | Disclaimers on landing, tool pages, every AI answer, dedicated page | all pages, `messages.py` | Look at each page |
| 14 | Input validation, file type/size/content checks, timeouts, friendly errors, rate limit | `utils/`, `gemini_service.py` | Upload `.exe`; run tests |
| 15 | Secrets in environment variables only; Colab Secrets support | `config.py`, notebook cell 4 | `/api/health` shows only true/false |
| 16 | Uploaded files never stored | `file_utils.py`, `ocr_service.py` | The `uploads/` folder stays empty |
| 17 | Colab notebook (11 cells) | `MediAI_Colab.ipynb` | Section 5 |
| 18 | Deployment (Docker + Render) | `Dockerfile`, section 8 | Open your Render link |
| 19 | Automatic tests (43) | `tests/` | `python -m unittest discover -s tests -v` |

---

## 11. Suggested 3-minute demo for the challenge

1. **Landing page** (10 s): say what MediAI is and read the disclaimer line.
2. **Report Explainer** (60 s): upload `sample_report.png`, show the *Low* hemoglobin card, then switch to **Telugu** and
   analyze again to show real explanations rather than transliteration.
3. **Symptom Checker** (60 s): click the throat, run a mild case; then type *chest pain and cannot breathe* and show
   the instant red 112 banner that appears **without waiting for the AI**.
4. **Medicine Info** (20 s): search *Dolo 650*, point at the "official label" badge and the absence of doses.
5. **Health Summary** (20 s): generate and download.
6. **Close** (10 s): "Rules handle emergencies, AI handles explanations, nothing is stored, and it never replaces a doctor."
