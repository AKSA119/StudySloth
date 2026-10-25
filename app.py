import os
import json
import re
from io import BytesIO
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

st.set_page_config(
    page_title="StudySloth | Less Stress. More Learning.",
    page_icon="🦥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Theme ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f6f7fc; color: #17203b; }
.block-container { padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 1500px; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#151d3b,#202957); }
section[data-testid="stSidebar"] * { color: #f7f8ff !important; }
.brand { font-family:'Plus Jakarta Sans',sans-serif; font-size:1.55rem; font-weight:800; color:#fff; }
.brand span { color:#a99aff; }
.tagline { color:#c8cde7; font-size:.82rem; margin-top:-7px; }
.hero-title { font-family:'Plus Jakarta Sans',sans-serif; font-size:1.9rem; font-weight:800; color:#17203b; margin-bottom:0; }
.muted { color:#65708d; }
.pill { display:inline-block; background:#eeeaff; color:#6451dc; padding:5px 10px; border-radius:30px; font-size:.78rem; font-weight:700; }
.panel { background:white; border:1px solid #e8ebf5; border-radius:18px; padding:18px 20px; box-shadow:0 5px 18px rgba(35,45,90,.035); margin-bottom:12px; }
.panel h3 { margin-top:0; color:#17203b; font-size:1.05rem; }
.metric { background:white; border:1px solid #e8ebf5; padding:15px 17px; border-radius:16px; }
.metric-number { font-family:'Plus Jakarta Sans',sans-serif; font-size:1.65rem; font-weight:800; color:#5c4ad4; }
.metric-label { color:#687391; font-size:.83rem; }
div.stButton > button { border-radius:11px; font-weight:700; min-height:2.65rem; }
.stButton > button[kind="primary"] { background:linear-gradient(90deg,#7764f6,#5e4bd7); border:0; }
div[data-testid="stFileUploader"] { background:#fbfbff; border:1px dashed #b8bdf0; border-radius:14px; padding:12px; }
.small-note { font-size:.8rem; color:#737e9c; }
</style>
""", unsafe_allow_html=True)

# ---------- State ----------
defaults = {
    "source_text": "",
    "source_name": "",
    "summary": "",
    "flashcards": [],
    "quiz": [],
    "plan": [],
    "quiz_answers": {},
    "quiz_submitted": False,
    "generated": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def get_setting(name: str, default: str = "") -> str:
    return (
        st.session_state.get(name)
        or os.getenv(name)
        or default
    ).strip()


def extract_pdf(uploaded_file) -> str:
    """Extract selectable text from an uploaded PDF."""
    reader = PdfReader(BytesIO(uploaded_file.getvalue()))
    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    text = "\n".join(pages).strip()

    if not text:
        raise ValueError(
            "No selectable text was found in this PDF. "
            "It may be scanned; OCR is not included in this version."
        )

    return text


def call_model(task_prompt: str, source: str) -> str:
    """Send study material to the configured OpenAI-compatible API."""
    api_key = get_setting("API_KEY")
    base_url = get_setting(
        "BASE_URL",
        "https://api.groq.com/openai/v1"
    ).rstrip("/")
    model = get_setting(
        "MODEL",
        "llama-3.3-70b-versatile"
    )

    if not api_key:
        raise RuntimeError(
            "Add your API key in Settings to use Live AI. "
            "Alternatively, select Demo mode."
        )

    endpoint = base_url + "/chat/completions"

    payload = {
        "model": model,
        "temperature": 0.3,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are StudySloth, a careful study assistant. "
                    "Use only the supplied study material. Do not invent "
                    "facts. If the material does not contain an answer, "
                    "say so. Follow the requested output format exactly."
                ),
            },
            {
                "role": "user",
                "content": (
                    task_prompt
                    + "\n\nSTUDY MATERIAL:\n"
                    + source[:12000]
                ),
            },
        ],
    }

    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"AI provider returned HTTP {response.status_code}: "
            f"{response.text[:700]}"
        )

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "The AI provider returned an unexpected response."
        ) from exc


def parse_json_response(raw: str) -> Any:
    """Parse JSON returned by the AI model."""
    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw.strip(),
        flags=re.I,
    )

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.S)

        if match:
            return json.loads(match.group(1))

        raise ValueError(
            "The model response wasn't valid JSON. Please try again."
        )


def build_study_pack(text: str, mode: str) -> dict:
    """Create a study pack from the supplied source text."""

    if mode == "Demo mode":
        return {
            "summary": (
                "## Demo mode\n\n"
                "Demo mode uses example content instead of generating "
                "material from your PDF. Select **Live open-weight AI** "
                "to generate a study pack from your own material."
            ),
            "flashcards": [
                {
                    "question": "How do I generate my own flashcards?",
                    "answer": (
                        "Select Live open-weight AI, provide your API "
                        "settings, and generate a revision pack."
                    ),
                }
            ],
            "quiz": [
                {
                    "question": (
                        "Which mode generates a pack from your own notes?"
                    ),
                    "options": [
                        "Demo mode",
                        "Live open-weight AI",
                        "Neither mode",
                        "Settings only",
                    ],
                    "answer_index": 1,
                    "explanation": (
                        "Live AI uses your supplied study material."
                    ),
                }
            ],
            "plan": [
                {
                    "task": "Configure your AI provider in Settings",
                    "duration": "5 min",
                },
                {
                    "task": "Upload or paste your study material",
                    "duration": "5 min",
                },
                {
                    "task": "Generate your revision pack in Live AI mode",
                    "duration": "5 min",
                },
            ],
        }

    prompt = """
Create a complete revision pack using ONLY the study material supplied
below. Every section must be based on that material, not on a generic
example or a different subject.

Return ONLY valid JSON with this exact schema:
{
  "summary": "Markdown summary with an overview and 4-8 key points",
  "flashcards": [
    {"question": "...", "answer": "..."}
  ],
  "quiz": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "answer_index": 0,
      "explanation": "..."
    }
  ],
  "plan": [
    {"task": "...", "duration": "10 min"}
  ]
}

Requirements:
- Create 5 flashcards.
- Create 3 multiple-choice quiz questions.
- Each quiz question must have exactly four options.
- answer_index must be an integer from 0 to 3.
- Create 3 short revision tasks.
- Keep the summary concise and focus on the most important concepts.
- Ground every question, answer, and task in the supplied material.
- Do not create Machine Learning content unless the supplied material
  is actually about Machine Learning.
- Do not use Markdown code fences.
"""

    raw = call_model(prompt, text)
    
    result = parse_json_response(raw)

    if not isinstance(result, dict):
        raise ValueError("The AI response must be a JSON object.")

    for key in ("summary", "flashcards", "quiz", "plan"):
        if key not in result:
            raise ValueError(
                f"AI response is missing the '{key}' field."
            )

    if not isinstance(result["summary"], str):
        raise ValueError("The AI summary must be text.")

    for key in ("flashcards", "quiz", "plan"):
        if not isinstance(result[key], list):
            raise ValueError(
                f"The AI response field '{key}' must be a list."
            )

    return result


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(
        '<div class="brand">🦥 Study<span>Sloth</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="tagline">Less Stress. More Learning.</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    page = st.radio(
        "YOUR WORKSPACE",
        [
            "🏠 Home",
            "📚 My Notes",
            "🗂️ Flashcards",
            "✍️ Quizzes",
            "🗓️ Revision Plan",
            "⚙️ Settings",
        ],
        label_visibility="visible",
    )

    st.markdown("---")
    st.markdown("**AI connection**")

    mode = st.selectbox(
        "Mode",
        ["Demo mode", "Live open-weight AI"],
        index=1,
        help=(
            "Demo mode uses an example. Live mode calls your configured "
            "OpenAI-compatible AI provider."
        ),
    )

    st.caption(
        "Use Live open-weight AI to create notes, flashcards, quizzes, "
        "and revision plans from your own study material."
    )

    st.markdown("---")
    st.markdown("**Your study streak**")
    st.markdown("🔥 **3 days**")
    st.caption("Small steps every day lead to big results.")


# ---------- Header ----------
h1, h2 = st.columns([3, 1.35])

with h1:
    st.markdown(
        '<div class="hero-title">☀️ Good morning, Learner!</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="muted">Upload your study material and let AI turn '
        'it into a complete revision pack.</div>',
        unsafe_allow_html=True,
    )

with h2:
    st.markdown(
        '<div class="panel" style="text-align:center;padding:12px;">'
        '✨ <b>Open-weight AI</b><br>'
        '<span class="small-note">Flexible · Model choice · Built for you'
        '</span></div>',
        unsafe_allow_html=True,
    )


# ---------- Home ----------
if page == "🏠 Home":
    col_upload, col_recent, col_check = st.columns([1.18, 1, 1])

    with col_upload:
        st.markdown(
            '<div class="panel"><h3>☁️ Upload Study Material</h3>'
            '<p class="muted">Turn a chapter into summaries, flashcards, '
            'quizzes, and a plan.</p></div>',
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "Drop a PDF here or browse files",
            type=["pdf"],
            help="PDF text extraction is supported; scanned PDFs need OCR.",
        )

        topic = st.text_input(
            "Or enter a topic / paste notes",
            placeholder="e.g. Operating Systems: Process Scheduling",
        )

        pasted = st.text_area(
            "Study notes (optional)",
            height=110,
            placeholder="Paste a chapter or your lecture notes here...",
        )

        # Optional PDF load button, retained from the original UI.
        if uploaded is not None:
            if st.button("📄 Load uploaded PDF", use_container_width=True):
                try:
                    extracted = extract_pdf(uploaded)
                    st.session_state.source_text = extracted
                    st.session_state.source_name = uploaded.name
                    st.session_state.generated = False
                    st.success(
                        f"Loaded {len(extracted):,} characters "
                        f"from {uploaded.name}"
                    )
                except Exception as exc:
                    st.error(str(exc))

        if st.button(
            "✨ Generate revision pack",
            type="primary",
            use_container_width=True,
        ):
            try:
                # Select the user's current source material.
                if pasted.strip():
                    chosen_text = pasted.strip()
                    source_name = "Pasted study notes"

                elif uploaded is not None:
                    # Extract the PDF immediately when Generate is clicked.
                    chosen_text = extract_pdf(uploaded)
                    source_name = uploaded.name

                elif st.session_state.source_text.strip():
                    chosen_text = st.session_state.source_text.strip()
                    source_name = (
                        st.session_state.source_name or "Loaded study material"
                    )

                elif topic.strip():
                    chosen_text = (
                        f"Study topic: {topic.strip()}\n"
                        "Explain the core concepts, definitions, examples, "
                        "and likely exam questions for this topic."
                    )
                    source_name = topic.strip()

                else:
                    chosen_text = ""
                    source_name = ""

                if not chosen_text:
                    st.warning(
                        "Upload a PDF, paste your notes, or enter a topic "
                        "before generating."
                    )

                elif len(chosen_text.strip()) < 60:
                    st.warning(
                        "Add a little more study material "
                        "(at least a few sentences) for useful results."
                    )

                else:
                    with st.spinner(
                        "StudySloth is preparing your revision pack..."
                    ):
                        pack = build_study_pack(chosen_text, mode)

                        st.session_state.source_text = chosen_text
                        st.session_state.source_name = source_name
                        st.session_state.summary = pack["summary"]
                        st.session_state.flashcards = pack["flashcards"]
                        st.session_state.quiz = pack["quiz"]
                        st.session_state.plan = pack["plan"]
                        st.session_state.quiz_answers = {}
                        st.session_state.quiz_submitted = False
                        st.session_state.generated = True
                        st.session_state.fc_index = 0
                        st.session_state.show_answer = False

                        st.success("Your revision pack is ready!")

            except Exception as exc:
                st.error(f"Couldn't generate the revision pack: {exc}")

                if mode == "Live open-weight AI":
                    st.info(
                        "Check Settings for your API key, base URL, "
                        "and model name."
                    )

    # ---------- Recent Study Material ----------
    with col_recent:
        st.markdown(
            '<div class="panel"><h3>🕘 Recent Study Material</h3></div>',
            unsafe_allow_html=True,
        )

        if st.session_state.generated:
            st.success("Latest revision pack")
            st.write(f"📄 **{st.session_state.source_name}**")
            st.caption(
                f"{len(st.session_state.source_text):,} characters processed"
            )
        else:
            st.caption(
                "Your latest uploaded or pasted study material will appear "
                "here after you generate a revision pack."
            )

        st.markdown(
            '<div class="panel"><h3>📈 Study Progress</h3>'
            '<p><b>57%</b> sample progress</p>'
            '<div class="small-note">Summaries · Flashcards · Quizzes · '
            'Revision plan</div></div>',
            unsafe_allow_html=True,
        )

    # ---------- Revision Checklist ----------
    with col_check:
        st.markdown(
            '<div class="panel" '
            'style="background:linear-gradient(135deg,#dff8ed,#dff5f8);">'
            '<h3>🦥 You’re doing great!</h3>'
            '<p>Consistency builds success.</p>'
            '<span style="font-size:2.5rem;">📖</span></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="panel"><h3>☑️ Revision Checklist</h3></div>',
            unsafe_allow_html=True,
        )

        tasks = st.session_state.plan

        if tasks:
            done = 0

            for i, task in enumerate(tasks[:7]):
                if st.checkbox(
                    f"{task.get('task', 'Revision task')} · "
                    f"{task.get('duration', '')}",
                    key=f"home_task_{i}",
                ):
                    done += 1

            st.progress(done / max(1, min(len(tasks), 7)))
            st.caption(f"{done}/{min(len(tasks), 7)} tasks completed")

        else:
            st.caption("Generate a revision pack to create your checklist.")

    # ---------- Generated Revision Pack ----------
    if st.session_state.generated:
        st.markdown("### Your revision pack")
        st.caption(f"Based on: {st.session_state.source_name}")

        tab1, tab2, tab3, tab4 = st.tabs(
            ["📘 Summary", "🗂️ Flashcards", "✍️ Quiz", "🗓️ Plan"]
        )

        with tab1:
            st.markdown(st.session_state.summary)
            st.download_button(
                "⬇️ Download summary",
                st.session_state.summary,
                file_name="studysloth_summary.md",
                mime="text/markdown",
            )

        with tab2:
            if st.session_state.flashcards:
                fc = st.session_state.flashcards[0]
                st.markdown(f"**Q:** {fc.get('question', '')}")

                with st.expander("Reveal answer"):
                    st.write(fc.get("answer", ""))

                st.caption(
                    f"{len(st.session_state.flashcards)} flashcards generated. "
                    "Open Flashcards to review them."
                )
            else:
                st.info("No flashcards were returned by the AI.")

        with tab3:
            st.write(
                f"{len(st.session_state.quiz)} practice questions generated. "
                "Open Quizzes to attempt them."
            )

        with tab4:
            for task in st.session_state.plan:
                st.write(
                    f"☐ {task.get('task', '')} — {task.get('duration', '')}"
                )

        export = {
            "source": st.session_state.source_name,
            "summary": st.session_state.summary,
            "flashcards": st.session_state.flashcards,
            "quiz": st.session_state.quiz,
            "plan": st.session_state.plan,
        }

        st.download_button(
            "📦 Download complete revision pack (JSON)",
            json.dumps(export, indent=2, ensure_ascii=False),
            file_name="studysloth_revision_pack.json",
            mime="application/json",
        )


# ---------- My Notes ----------
elif page == "📚 My Notes":
    st.title("📚 My Notes")

    if st.session_state.summary:
        st.caption(f"Source: {st.session_state.source_name}")
        st.markdown(st.session_state.summary)

        st.download_button(
            "Download notes as Markdown",
            st.session_state.summary,
            "studysloth_notes.md",
            "text/markdown",
        )

    else:
        st.info(
            "Your generated chapter summary will appear here. Go to Home, "
            "upload or paste your own study material, and generate a revision pack."
        )


# ---------- Flashcards ----------
elif page == "🗂️ Flashcards":
    st.title("🗂️ Flashcards")

    cards = st.session_state.flashcards

    if not cards:
        st.info(
            "No flashcards yet. Go to Home and generate a revision pack "
            "from your own study material."
        )

    else:
        if "fc_index" not in st.session_state:
            st.session_state.fc_index = 0

        idx = st.session_state.fc_index % len(cards)
        card = cards[idx]

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.caption(f"CARD {idx + 1} OF {len(cards)}")
        st.subheader(card.get("question", "Question"))

        if st.button("🔄 Flip card"):
            st.session_state["show_answer"] = not st.session_state.get(
                "show_answer", False
            )

        if st.session_state.get("show_answer", False):
            st.success(card.get("answer", "No answer available."))

        st.markdown("</div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 1, 2])

        with c1:
            if st.button("← Previous"):
                st.session_state.fc_index = (idx - 1) % len(cards)
                st.session_state.show_answer = False
                st.rerun()

        with c2:
            if st.button("Next →"):
                st.session_state.fc_index = (idx + 1) % len(cards)
                st.session_state.show_answer = False
                st.rerun()

        with c3:
            st.caption("Tip: say the answer out loud before flipping the card.")


# ---------- Quizzes ----------
elif page == "✍️ Quizzes":
    st.title("✍️ Practice Quiz")

    questions = st.session_state.quiz

    if not questions:
        st.info(
            "No quiz questions yet. Go to Home and generate a revision pack "
            "from your own study material."
        )

    else:
        with st.form("quiz_form"):
            for i, q in enumerate(questions):
                st.markdown(f"**{i + 1}. {q.get('question', '')}**")
                opts = q.get("options", [])

                st.radio(
                    "Choose one",
                    opts,
                    key=f"quiz_{i}",
                    index=None,
                    label_visibility="collapsed",
                )

            submitted = st.form_submit_button(
                "Check my answers",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            score = 0

            for i, q in enumerate(questions):
                selected = st.session_state.get(f"quiz_{i}")
                correct_idx = q.get("answer_index", 0)
                options = q.get("options", [])

                correct = (
                    options[correct_idx]
                    if isinstance(correct_idx, int)
                    and 0 <= correct_idx < len(options)
                    else ""
                )

                if selected == correct:
                    score += 1

            st.session_state.quiz_score = score
            st.session_state.quiz_submitted = True

        if st.session_state.get("quiz_submitted"):
            score = st.session_state.get("quiz_score", 0)

            st.metric(
                "Your score",
                f"{score}/{len(questions)}",
                f"{round(score / max(1, len(questions)) * 100)}%",
            )

            for i, q in enumerate(questions):
                opts = q.get("options", [])
                ci = q.get("answer_index", 0)

                correct = (
                    opts[ci]
                    if isinstance(ci, int) and 0 <= ci < len(opts)
                    else "Not specified"
                )

                st.write(f"**Q{i + 1} answer:** {correct}")
                st.caption(q.get("explanation", ""))


# ---------- Revision Plan ----------
elif page == "🗓️ Revision Plan":
    st.title("🗓️ Your Revision Plan")

    plan = st.session_state.plan

    if not plan:
        st.info(
            "No revision plan yet. Go to Home and generate a revision pack "
            "from your own study material."
        )

    else:
        st.caption("A manageable plan designed for short, focused study sessions.")

        for i, task in enumerate(plan):
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])

                with c1:
                    st.checkbox(
                        task.get("task", "Revision task"),
                        key=f"plan_{i}",
                    )

                with c2:
                    st.caption(task.get("duration", "10 min"))

        st.info("Try one task at a time. Small steps every day lead to big results.")


# ---------- Settings ----------
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    st.write(
        "Connect a hosted inference provider that supports the OpenAI "
        "Chat Completions API. Choose a model supported by your provider."
    )

    with st.form("settings_form"):
        api_key = st.text_input(
            "Provider API key",
            value=st.session_state.get("API_KEY", os.getenv("API_KEY", "")),
            type="password",
            help=(
                "Stored only in this running app session; "
                "do not commit keys to GitHub."
            ),
        )

        base_url = st.text_input(
            "API base URL",
            value=st.session_state.get(
                "BASE_URL",
                os.getenv("BASE_URL", "https://api.groq.com/openai/v1"),
            ),
        )

        model = st.text_input(
            "Model ID",
            value=st.session_state.get(
                "MODEL",
                os.getenv("MODEL", "llama-3.3-70b-versatile"),
            ),
        )

        save = st.form_submit_button("Save settings", type="primary")

    if save:
        st.session_state["API_KEY"] = api_key.strip()
        st.session_state["BASE_URL"] = base_url.strip()
        st.session_state["MODEL"] = model.strip()
        st.success("Settings saved for this running session.")

    st.markdown("### Recommended setup")

    st.markdown("""
1. Create an account with a hosted inference provider.
2. Select a model supported by that provider.
3. Copy its OpenAI-compatible base URL, model ID, and API key.
4. Enter them above and choose **Live open-weight AI** in the sidebar.
""")

    st.warning(
        "Hosted inference sends the text you submit to the chosen provider. "
        "Do not upload sensitive personal, academic, or confidential data "
        "unless you trust that provider's privacy and retention terms."
    )

    st.markdown("### Privacy & limitations")

    st.markdown("""
- PDF text is extracted in the app and sent to the configured model only when you generate a pack in Live mode.
- This prototype does not include user accounts, a database, or cloud file storage.
- Scanned PDFs need OCR, which is not included.
- Provider model names and free-tier limits can change; check your provider's current documentation.
""")
