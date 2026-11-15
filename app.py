import os
import time
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from gnani.stt import GnaniSTTClient
from gnani.tts import GnaniTTSClient, AudioConfig

# ==================================================
# 1. CONFIGURATION
# ==================================================

load_dotenv()

GNANI_API_KEY = os.getenv("GNANI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


st.set_page_config(
    page_title="AI Student Voice Assistant",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)


LANGUAGES = {
    "Auto Detect": "indic-auto",
    "English": "en-IN",
    "Telugu": "te-IN",
    "Hindi": "hi-IN",
    "Tamil": "ta-IN",
    "Kannada": "kn-IN",
    "Malayalam": "ml-IN",
    "Marathi": "mr-IN",
    "Bengali": "bn-IN",
    "Gujarati": "gu-IN"
}

VOICES = ["Kaveri", "Nalini", "Asmita", "Suhana"]

PAGES = [
    "Dashboard",
    "Voice Assistant",
    "Text Assistant",
    "Chat History",
    "Settings"
]

# UI only
PAGE_ICONS = {
    "Dashboard": "🏠",
    "Voice Assistant": "🎤",
    "Text Assistant": "💬",
    "Chat History": "📚",
    "Settings": "⚙️"
}

EXAMPLE_QUESTIONS = [
    "Explain Artificial Intelligence in simple words",
    "What is the Pythagoras theorem?",
    "How does photosynthesis work?"
]

# ==================================================
# 2. SESSION STATE
# ==================================================

DEFAULTS = {
    "page": "Dashboard",
    "page_navigation": "Dashboard",
    "language": "English",
    "voice": "Kaveri",
    "transcript": "",
    "detected_language": "",
    "answer": "",
    "generated_audio": None,
    "history": [],
    "current_question": "",
    "current_source": ""
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==================================================
# 3. NAVIGATION FUNCTIONS
# ==================================================

def navigate_to(page):
    st.session_state.page = page
    st.session_state.page_navigation = page


def sync_page():
    st.session_state.page = st.session_state.page_navigation


def use_example(text):
    # UI helper: fills the Text Assistant box with an example question
    st.session_state.dashboard_text_question = text


# ==================================================
# 3B. SMALL UI HELPERS (no backend logic)
# ==================================================

def h(markup):
    st.markdown(markup, unsafe_allow_html=True)


def empty_state(title, text):
    h(
        '<div class="empty-box">'
        f'<b>{title}</b><br>{text}'
        '</div>'
    )


def step_bar(labels, done_flags):
    active_index = next(
        (i for i, done in enumerate(done_flags) if not done),
        len(labels)
    )
    parts = ""
    for i, label in enumerate(labels):
        if done_flags[i]:
            css, mark = "done", "✓"
        elif i == active_index:
            css, mark = "active", str(i + 1)
        else:
            css, mark = "", str(i + 1)
        parts += (
            f'<div class="step {css}">'
            f'<div class="step-num">{mark}</div>{label}</div>'
        )
    h(f'<div class="steps">{parts}</div>')


def history_frame():
    rows = []
    for number, item in enumerate(reversed(st.session_state.history), start=1):
        rows.append({
            "No.": number,
            "Time": item["time"],
            "Source": item["source"],
            "Question": item["question"],
            "Words": len(item["answer"].split())
        })
    return pd.DataFrame(
        rows,
        columns=["No.", "Time", "Source", "Question", "Words"]
    )


# ==================================================
# 5. API KEY CHECK
# ==================================================

if not GNANI_API_KEY:
    st.error("Gnani API key is missing. Check your .env file.")
    st.stop()

if not GROQ_API_KEY:
    st.error("Groq API key is missing. Check your .env file.")
    st.stop()


# ==================================================
# 6. GENERATE AI ANSWER
# ==================================================

def generate_answer(question):

    client = Groq(api_key=GROQ_API_KEY)

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful multilingual AI assistant. "
                    "Answer questions about education, science, "
                    "technology, mathematics and general knowledge. "
                    "Give clear and accurate answers. "
                    "Reply in the same language as the user's question."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ],
        max_completion_tokens=1024,
        reasoning_effort="low"
    )

    return response.choices[0].message.content


# ==================================================
# 7. GENERATE SPEECH
# ==================================================

def generate_speech(answer):

    client = GnaniTTSClient(api_key=GNANI_API_KEY)

    language = LANGUAGES[st.session_state.language]

    if language == "indic-auto":
        language = st.session_state.detected_language or "auto"

    last_error = None

    for attempt in range(2):
        try:

            audio_data = client.synthesize(
                answer[:800],
                voice=st.session_state.voice,
                model="timbre-v2.5",
                language=language,
                speed=1.0,
                audio_config=AudioConfig(
                    sample_rate=48000,
                    encoding="linear_pcm",
                    container="wav"
                )
            )

            if audio_data and len(audio_data) > 100:
                return bytes(audio_data)

            raise ValueError("No valid audio data returned.")

        except Exception as error:
            last_error = error

            if attempt == 0:
                time.sleep(2)

    raise last_error


# ==================================================
# 8. SAVE HISTORY
# ==================================================

def save_history(question, answer, source):

    st.session_state.history.insert(
        0,
        {
            "question": question,
            "answer": answer,
            "source": source,
            "time": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        }
    )


# ==================================================
# 9. PROCESS QUESTION
# ==================================================

def process_question(question, source):

    if not question or not question.strip():
        st.warning("Please enter or record a question.")
        return

    try:

        with st.spinner("AI is generating your answer..."):
            answer = generate_answer(question.strip())

        if answer and answer.strip():

            st.session_state.answer = answer.strip()
            st.session_state.generated_audio = None
            st.session_state.current_question = question.strip()
            st.session_state.current_source = source

            save_history(
                question.strip(),
                answer.strip(),
                source
            )

            st.success("AI answer generated successfully!")

        else:
            st.error("AI did not return an answer.")

    except Exception as error:
        st.error("AI answer generation failed.")
        st.code(str(error))


# ==================================================
# 10. DISPLAY ANSWER (presentation only)
# ==================================================

def show_answer():

    if st.session_state.answer:

        with st.container(border=True):

            h('<div class="ans-label">💡 AI Generated Answer</div>')

            st.write(st.session_state.answer)

            st.caption(
                f"{len(st.session_state.answer.split())} words"
            )


# ==================================================
# 11. SPEAK ANSWER
# ==================================================

def speak_answer():

    if not st.session_state.answer:
        st.warning("Generate an AI answer first.")
        return

    try:

        with st.spinner("Gnani Timbre is generating speech..."):

            audio = generate_speech(
                st.session_state.answer
            )

        st.session_state.generated_audio = audio

        st.success("Voice response generated successfully!")

    except Exception as error:
        st.error("Voice generation failed.")
        st.code(str(error))


# ==================================================
# 12. DISPLAY AUDIO (presentation only)
# ==================================================

def show_audio():

    if st.session_state.generated_audio:

        with st.container(border=True):

            h('<div class="ans-label">🎧 Listen to AI Voice Response</div>')

            st.audio(
                st.session_state.generated_audio,
                format="audio/wav"
            )

            st.download_button(
                "⬇️ Download Voice Response",
                data=st.session_state.generated_audio,
                file_name="AI_Student_Voice_Response.wav",
                mime="audio/wav"
            )


# ==================================================
# VERSION 1 UI: PROFESSIONAL CORPORATE DASHBOARD
# Navy and white, sidebar + top bar, analytics-first
# ==================================================

NAVY = "#12265a"
BLUE = "#2f5fd0"

h("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="st-"], .stApp, button, input, textarea {
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
.stApp { background: #f2f4f9; }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container {
    max-width: 1280px; padding-top: 1.2rem !important;
    padding-bottom: 3rem !important; overflow: visible !important;
}
h1, h2, h3 { color: #12265a; line-height: 1.4 !important; overflow: visible !important; }

/* Sidebar */
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child { background: #0f1f4b; }
[data-testid="stSidebar"] * { color: #ffffff; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color: #9fb0d8 !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12); }
.brand { display: flex; align-items: center; gap: 12px; padding: 4px 0; }
.brand-logo {
    width: 42px; height: 42px; border-radius: 10px; background: #2f5fd0;
    display: flex; align-items: center; justify-content: center; font-size: 21px;
}
.brand-name { font-size: 17px; font-weight: 700; line-height: 1.2; }
.brand-sub { font-size: 12px; color: #9fb0d8; }
.nav-title { font-size: 12px; font-weight: 600; color: #9fb0d8 !important; margin: 2px 0 6px 2px; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: 3px; }
[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 11px 14px; border-radius: 6px; width: 100%; cursor: pointer;
    border-left: 3px solid transparent; transition: background 0.2s ease;
}
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,0.07); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: rgba(255,255,255,0.13); border-left-color: #8fb0f2;
}
[data-testid="stSidebar"] [role="radiogroup"] label p { color: #fff !important; font-weight: 500; font-size: 14.5px; }
.side-status {
    display: flex; align-items: center; gap: 10px; background: rgba(255,255,255,0.07);
    padding: 10px 14px; border-radius: 8px; font-size: 13px; font-weight: 500; margin: 6px 0;
}
.dot { width: 8px; height: 8px; border-radius: 50%; background: #3ddc97; }

/* Top bar */
.topbar {
    display: flex; justify-content: space-between; align-items: center;
    background: #fff; border: 1px solid #e1e6f2; border-radius: 10px;
    padding: 0 18px; min-height: 46px;
}
.crumb { color: #7a869f; font-size: 13px; }
.crumb-sep { color: #b4bdd0; margin: 0 6px; }
.crumb-now { color: #12265a; font-weight: 700; font-size: 14px; }
.chip {
    background: #eef2fb; color: #2a3d7a; border-radius: 6px;
    padding: 4px 10px; font-size: 12px; font-weight: 600; margin-left: 8px;
}

/* Titles */
.page-title { color: #12265a; font-size: 26px; font-weight: 800; margin: 20px 0 2px 0; }
.page-sub { color: #6b7790; font-size: 14px; margin-bottom: 18px; }
.sec { color: #12265a; font-size: 16px; font-weight: 700; margin: 22px 0 10px 0; padding-left: 10px; border-left: 4px solid #2f5fd0; }

/* KPI */
.kpi {
    background: #fff; border: 1px solid #e1e6f2; border-left: 4px solid #12265a;
    border-radius: 10px; padding: 18px 20px; min-height: 118px;
    transition: box-shadow 0.2s ease;
}
.kpi:hover { box-shadow: 0 8px 22px rgba(18,38,90,0.12); }
.kpi-label { color: #6b7790; font-size: 13px; font-weight: 600; }
.kpi-value { color: #12265a; font-size: 30px; font-weight: 800; margin-top: 8px; }
.kpi-note { color: #8a94ab; font-size: 12px; margin-top: 2px; }

/* Service + feature cards */
.svc {
    display: flex; align-items: center; gap: 14px; background: #fff;
    border: 1px solid #e1e6f2; border-radius: 10px; padding: 16px 18px;
}
.svc-icon { width: 40px; height: 40px; border-radius: 8px; background: #eef2fb; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.svc-name { color: #12265a; font-weight: 700; font-size: 14px; }
.svc-role { color: #7a869f; font-size: 12px; }
.ok { margin-left: auto; background: #e5f6ed; color: #17703f; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600; }
.feature { background: #fff; border: 1px solid #e1e6f2; border-radius: 10px; padding: 16px 18px; margin-bottom: 8px; min-height: 104px; }
.feature h4 { margin: 0 0 4px 0; color: #12265a; font-size: 15px; }
.feature p { margin: 0; color: #6b7790; font-size: 13px; line-height: 1.6; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #fff; border-radius: 10px; border: 1px solid #e1e6f2 !important;
}

/* Buttons */
div.stButton > button, div.stDownloadButton > button {
    background: #12265a; color: #fff; border: 1px solid #12265a; border-radius: 8px;
    min-height: 44px; font-weight: 600; transition: background 0.2s ease, transform 0.15s ease;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background: #1d3a8a; border-color: #1d3a8a; color: #fff; transform: translateY(-1px);
}
div.stButton > button:active { color: #fff; transform: translateY(0); }
div.stButton > button:focus-visible { outline: 3px solid #b6c8f5; }

div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input {
    border-radius: 8px; background: #fff; border: 1px solid #d3dbec; font-size: 15px;
}
div[data-testid="stTextArea"] textarea:focus { border-color: #2f5fd0; box-shadow: 0 0 0 3px rgba(47,95,208,0.18); }
div[data-baseweb="select"] > div { border-radius: 8px; }
div[data-testid="stAlert"] { border-radius: 8px; }
button[data-baseweb="tab"] { font-weight: 600; }

/* Steps */
.steps { display: flex; gap: 8px; margin: 0 0 16px 0; flex-wrap: wrap; }
.step {
    flex: 1; min-width: 130px; display: flex; align-items: center; gap: 10px;
    background: #fff; border: 1px solid #e1e6f2; border-radius: 8px;
    padding: 10px 14px; color: #8a94ab; font-size: 13px; font-weight: 600;
}
.step-num { width: 24px; height: 24px; border-radius: 6px; background: #e8ecf6; color: #6b7790; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
.step.active { color: #12265a; border-color: #2f5fd0; }
.step.active .step-num { background: #2f5fd0; color: #fff; }
.step.done { color: #12265a; }
.step.done .step-num { background: #17a363; color: #fff; }

.ans-label { color: #12265a; font-weight: 700; font-size: 15px; margin-bottom: 6px; }
.empty-box { background: #fff; border: 1px dashed #c3cde4; border-radius: 10px; padding: 34px 20px; text-align: center; color: #6b7790; font-size: 14px; line-height: 1.7; }
.empty-box b { color: #12265a; font-size: 15px; }
.pill { display: inline-block; padding: 3px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; background: #e4ebfb; color: #1d3a8a; }
.pill.text { background: #e8ebf3; color: #3b4766; }
.footer { text-align: center; color: #8a94ab; font-size: 12px; padding: 20px; }

@media (max-width: 768px) { .page-title { font-size: 22px; } .topbar { flex-direction: column; align-items: flex-start; padding: 10px 14px; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
""")


def style_chart(chart, height=250):
    return (
        chart.properties(height=height)
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor="#6b7790", titleColor="#6b7790",
            gridColor="#e6eaf4", domainColor="#cfd6e6"
        )
        .configure_legend(labelColor="#12265a", titleColor="#6b7790")
    )


def top_bar(title):
    c1, c2, c3 = st.columns([5, 1.4, 1.4])
    with c1:
        h(
            '<div class="topbar"><div>'
            '<span class="crumb">Workspace</span><span class="crumb-sep">/</span>'
            f'<span class="crumb-now">{title}</span></div><div>'
            f'<span class="chip">🌐 {st.session_state.language}</span>'
            f'<span class="chip">🔊 {st.session_state.voice}</span>'
            f'<span class="chip">📅 {datetime.now().strftime("%d %b %Y")}</span>'
            '</div></div>'
        )
    with c2:
        st.button(
            "🎤 Ask by voice", key="top_voice", use_container_width=True,
            on_click=navigate_to, args=("Voice Assistant",)
        )
    with c3:
        st.button(
            "💬 Ask by text", key="top_text", use_container_width=True,
            on_click=navigate_to, args=("Text Assistant",)
        )


def page_title(title, sub):
    h(f'<div class="page-title">{title}</div><div class="page-sub">{sub}</div>')


def section(title):
    h(f'<div class="sec">{title}</div>')


def kpi(label, value, note=""):
    h(
        '<div class="kpi">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-note">{note}</div></div>'
    )


# ==================================================
# 13. SIDEBAR NAVIGATION
# ==================================================

with st.sidebar:

    h(
        '<div class="brand"><div class="brand-logo">🎙️</div><div>'
        '<div class="brand-name">AI Assistant</div>'
        '<div class="brand-sub">Multilingual Student Companion</div></div></div>'
    )

    st.divider()

    h('<div class="nav-title">Navigation</div>')

    st.radio(
        "Choose a page",
        PAGES,
        key="page_navigation",
        label_visibility="collapsed",
        on_change=sync_page,
        format_func=lambda name: f"{PAGE_ICONS[name]}  {name}"
    )

    st.divider()

    h('<div class="nav-title">API Status</div>')
    h('<div class="side-status"><span class="dot"></span>Gnani API Connected</div>')
    h('<div class="side-status"><span class="dot"></span>Groq API Connected</div>')

    st.divider()

    h('<div class="nav-title">AI Models</div>')
    st.caption("🎤 Prisma - Speech to Text")
    st.caption("🧠 Groq - Answer Generation")
    st.caption("🔊 Timbre - Text to Speech")

    st.divider()

    st.caption("AI Student Voice Assistant")
    st.caption("Version 1.0")


# ==================================================
# 14. DASHBOARD PAGE
# ==================================================

if st.session_state.page == "Dashboard":

    top_bar("Dashboard")

    page_title("Dashboard", "Overview of your assistant activity and connected services.")

    history = st.session_state.history
    voice_count = sum(1 for item in history if item["source"] == "Voice")
    text_count = sum(1 for item in history if item["source"] == "Text")
    frame = history_frame()
    average_words = int(frame["Words"].mean()) if len(frame) else 0

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi("💬 Questions Asked", len(history), "This session")
    with k2:
        kpi("🎤 Voice Questions", voice_count, "Asked by microphone")
    with k3:
        kpi("⌨️ Text Questions", text_count, "Typed in the text box")
    with k4:
        kpi("📝 Average Answer Length", average_words, "Words per answer")

    section("Analytics")

    c1, c2 = st.columns([1, 1.5])

    with c1:
        with st.container(border=True):
            st.markdown("**Questions by input type**")

            if history:
                source_df = pd.DataFrame({
                    "Source": ["Voice", "Text"],
                    "Questions": [voice_count, text_count]
                })

                chart = alt.Chart(source_df).mark_bar(
                    cornerRadius=4, size=30
                ).encode(
                    y=alt.Y("Source:N", title=None),
                    x=alt.X("Questions:Q", axis=alt.Axis(tickMinStep=1)),
                    color=alt.Color(
                        "Source:N", legend=None,
                        scale=alt.Scale(domain=["Voice", "Text"], range=[BLUE, NAVY])
                    ),
                    tooltip=["Source:N", "Questions:Q"]
                ).interactive()

                st.altair_chart(style_chart(chart), use_container_width=True)
            else:
                empty_state("No data yet", "Ask a question to see this chart.")

    with c2:
        with st.container(border=True):
            st.markdown("**Answer length per question (words)**")

            if history:
                chart = alt.Chart(frame).mark_bar(
                    cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=NAVY
                ).encode(
                    x=alt.X("No.:O", title="Question"),
                    y=alt.Y("Words:Q"),
                    tooltip=["No.:O", "Question:N", "Source:N", "Words:Q"]
                ).interactive()

                st.altair_chart(style_chart(chart), use_container_width=True)
            else:
                empty_state("No data yet", "Answer lengths appear after your first question.")

    section("Recent activity")

    if history:
        st.dataframe(
            frame[["Time", "Source", "Question", "Words"]].iloc[::-1].head(5),
            use_container_width=True,
            hide_index=True
        )
    else:
        empty_state("No recent activity", "Your latest questions will be listed here.")

    section("Connected services")

    s1, s2, s3 = st.columns(3)

    services = [
        ("🎤", "Gnani Prisma", "Speech recognition"),
        ("🧠", "Groq GPT-OSS 20B", "Answer generation"),
        ("🔊", "Gnani Timbre", "Voice generation")
    ]

    for column, (icon, name, role) in zip((s1, s2, s3), services):
        with column:
            h(
                f'<div class="svc"><div class="svc-icon">{icon}</div><div>'
                f'<div class="svc-name">{name}</div><div class="svc-role">{role}</div></div>'
                '<span class="ok">Connected</span></div>'
            )

    section("Quick access")

    q1, q2, q3, q4 = st.columns(4)

    with q1:
        h('<div class="feature"><h4>🎤 Voice Assistant</h4><p>Speak your questions and receive spoken AI answers.</p></div>')
        st.button("Open Voice Assistant", key="open_voice", use_container_width=True,
                  on_click=navigate_to, args=("Voice Assistant",))

    with q2:
        h('<div class="feature"><h4>💬 Text Assistant</h4><p>Type any question and get an intelligent AI answer.</p></div>')
        st.button("Open Text Assistant", key="open_text", use_container_width=True,
                  on_click=navigate_to, args=("Text Assistant",))

    with q3:
        h('<div class="feature"><h4>📚 Chat History</h4><p>Review your previous questions and AI answers.</p></div>')
        st.button("View Chat History", key="open_history", use_container_width=True,
                  on_click=navigate_to, args=("Chat History",))

    with q4:
        h('<div class="feature"><h4>⚙️ Settings</h4><p>Change your language and AI voice preferences.</p></div>')
        st.button("Open Settings", key="open_settings", use_container_width=True,
                  on_click=navigate_to, args=("Settings",))


# ==================================================
# 15. VOICE ASSISTANT PAGE
# ==================================================

elif st.session_state.page == "Voice Assistant":

    top_bar("Voice Assistant")

    page_title("🎤 Voice Assistant", "Ask your question using your microphone.")

    step_bar(
        ["Record", "Transcript", "AI answer", "Voice reply"],
        [
            bool(st.session_state.transcript),
            bool(st.session_state.transcript),
            bool(st.session_state.answer),
            st.session_state.generated_audio is not None
        ]
    )

    left, right = st.columns([1, 1.3], gap="large")

    with left:

        with st.container(border=True):

            st.markdown("### Step 1: Record Your Question")

            audio_input = st.audio_input("Record your voice")

            if st.button(
                "Convert Speech to Text",
                type="primary",
                key="convert_speech",
                use_container_width=True
            ):

                if audio_input is None:
                    st.warning("Please record your voice first.")

                else:

                    try:

                        client = GnaniSTTClient(
                            api_key=GNANI_API_KEY
                        )

                        with st.spinner("Prisma is recognizing your speech..."):

                            audio_input.seek(0)

                            result = client.transcribe(
                                audio_input,
                                language_code=LANGUAGES[
                                    st.session_state.language
                                ],
                                model="prisma-v3.0",
                                format="transcribe"
                            )

                        transcript = result.get("transcript", "")

                        if transcript:

                            st.session_state.transcript = transcript

                            st.session_state.detected_language = (
                                result.get("detected_language_code", "")
                            )

                            st.session_state.answer = ""
                            st.session_state.generated_audio = None

                            st.success("Speech converted successfully!")

                        else:
                            st.warning("No speech detected.")

                    except Exception as error:
                        st.error("Speech recognition failed.")
                        st.code(str(error))

    with right:

        if st.session_state.transcript:

            with st.container(border=True):

                st.markdown("### Step 2: Your Transcript")

                st.info(st.session_state.transcript)

                if st.session_state.detected_language:
                    st.caption(
                        "Detected language: "
                        + st.session_state.detected_language
                    )

                if st.button(
                    "Generate AI Answer",
                    type="primary",
                    key="voice_generate",
                    use_container_width=True
                ):

                    process_question(
                        st.session_state.transcript,
                        "Voice"
                    )

        else:
            empty_state("Transcript will appear here", "Record a question and convert it to text.")

        if st.session_state.answer:

            show_answer()

            if st.button(
                "Speak AI Answer",
                type="primary",
                key="voice_speak",
                use_container_width=True
            ):
                speak_answer()

            show_audio()


# ==================================================
# 16. TEXT ASSISTANT PAGE
# ==================================================

elif st.session_state.page == "Text Assistant":

    top_bar("Text Assistant")

    page_title("💬 Text Assistant", "Ask questions about any topic.")

    with st.container(border=True):

        st.markdown("**Quick prompts**")

        e1, e2, e3 = st.columns(3)

        for column, number in zip((e1, e2, e3), range(3)):
            with column:
                st.button(
                    EXAMPLE_QUESTIONS[number],
                    key=f"example_{number}",
                    use_container_width=True,
                    on_click=use_example,
                    args=(EXAMPLE_QUESTIONS[number],)
                )

        question = st.text_area(
            "Enter your question",
            key="dashboard_text_question",
            placeholder="Example: Explain Artificial Intelligence...",
            height=150
        )

        if st.button(
            "Generate AI Answer",
            type="primary",
            key="text_generate",
            use_container_width=True
        ):
            process_question(question, "Text")

    if st.session_state.answer:

        show_answer()

        if st.button(
            "Speak AI Answer",
            type="primary",
            key="text_speak"
        ):
            speak_answer()

        show_audio()


# ==================================================
# 17. CHAT HISTORY PAGE
# ==================================================

elif st.session_state.page == "Chat History":

    top_bar("Chat History")

    page_title("📚 Chat History", "Review your previous questions and answers.")

    if not st.session_state.history:

        empty_state("No chat history available yet", "Your questions and answers will be listed here.")

    else:

        f1, f2, f3 = st.columns([2.2, 1, 1])

        with f1:
            search_text = st.text_input(
                "Search questions and answers",
                key="history_search",
                placeholder="Type a keyword..."
            )

        with f2:
            source_filter = st.selectbox(
                "Input type",
                ["All", "Voice", "Text"],
                key="history_source_filter"
            )

        with f3:
            st.metric("Total questions", len(st.session_state.history))

        matches = []

        for index, item in enumerate(st.session_state.history):

            if source_filter != "All" and item["source"] != source_filter:
                continue

            if search_text and search_text.lower() not in (
                item["question"] + " " + item["answer"]
            ).lower():
                continue

            matches.append((index, item))

        if matches:

            section("Summary")

            st.dataframe(
                pd.DataFrame([
                    {
                        "No.": index + 1,
                        "Time": item["time"],
                        "Source": item["source"],
                        "Question": item["question"]
                    }
                    for index, item in matches
                ]),
                use_container_width=True,
                hide_index=True
            )

            section("Details")

            for index, item in matches:

                with st.expander(
                    f"Question {index + 1} - {item['time']}"
                ):

                    st.markdown("**Question:**")
                    st.write(item["question"])

                    st.markdown("**AI Answer:**")
                    st.write(item["answer"])

                    pill_class = "pill" if item["source"] == "Voice" else "pill text"
                    h(f'<span class="{pill_class}">Source: {item["source"]}</span>')

        else:
            st.info("No conversations match your filters.")

        if st.button("Clear Chat History", key="clear_history"):

            st.session_state.history = []

            st.success("Chat history cleared.")

            st.rerun()


# ==================================================
# 18. SETTINGS PAGE
# ==================================================

elif st.session_state.page == "Settings":

    top_bar("Settings")

    page_title("⚙️ Settings", "Customize your AI assistant.")

    with st.container(border=True):

        tab_a, tab_b, tab_c = st.tabs(
            ["🌐 Language", "🔊 Voice", "ℹ️ Services and about"]
        )

        with tab_a:

            st.markdown("### 🌐 Language Preferences")

            language_names = list(LANGUAGES.keys())

            new_language = st.selectbox(
                "Select application language",
                language_names,
                index=language_names.index(
                    st.session_state.language
                ),
                key="settings_language"
            )

        with tab_b:

            st.markdown("### 🔊 Voice Preferences")

            new_voice = st.selectbox(
                "Select AI voice",
                VOICES,
                index=VOICES.index(
                    st.session_state.voice
                ),
                key="settings_voice"
            )

        with tab_c:

            st.markdown("### 🔌 Connected AI Services")

            st.success("Gnani Prisma V3.0")
            st.success("Groq GPT-OSS 20B")
            st.success("Gnani Timbre V2.5")

            st.markdown("### ℹ️ Application Information")

            st.write("Application: AI Student Voice Assistant")
            st.write("Interface: Streamlit")
            st.write("Programming Language: Python")
            st.write("Version: 1.0")

    if st.button(
        "Save Settings",
        type="primary",
        key="save_settings"
    ):

        st.session_state.language = new_language
        st.session_state.voice = new_voice

        st.success("Settings saved successfully!")


# ==================================================
# 19. FOOTER
# ==================================================

st.divider()

h('<div class="footer">AI Student Voice Assistant | Powered by Gnani AI and Groq</div>')
