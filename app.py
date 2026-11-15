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
# VERSION 3 UI: FUTURISTIC AI DASHBOARD
# Dark glassmorphism, electric blue and cyan, command-center layout
# ==================================================

CYAN = "#22d3ee"
ELECTRIC = "#3b82f6"

h("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="st-"], .stApp, button, input, textarea {
    font-family: 'Space Grotesk', 'Segoe UI', sans-serif;
}
.stApp {
    background:
        radial-gradient(1000px 520px at 88% -8%, rgba(34,211,238,0.16), transparent 60%),
        radial-gradient(900px 600px at -8% 24%, rgba(59,130,246,0.20), transparent 60%),
        #060b1c;
    color: #dbe7ff;
}
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container {
    max-width: 1320px; padding-top: 2rem !important;
    padding-bottom: 3rem !important; overflow: visible !important;
}

/* Text colours on dark */
h1, h2, h3, h4 { color: #ffffff; line-height: 1.4 !important; overflow: visible !important; }
.stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stMarkdownContainer"] li,
.stApp [data-testid="stWidgetLabel"] p,
.stApp [data-testid="stMetricLabel"] p { color: #dbe7ff; }
.stApp [data-testid="stCaptionContainer"] p { color: #8fa6cc; }
.stApp [data-testid="stMetricValue"] { color: #67e8f9; font-family: 'JetBrains Mono', monospace; }

/* Sidebar */
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
    background: #070d22; border-right: 1px solid rgba(255,255,255,0.08);
}
[data-testid="stSidebar"] * { color: #dbe7ff; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.10); }
.core {
    display: flex; align-items: center; gap: 12px; padding: 4px 0;
}
.core-orb {
    width: 42px; height: 42px; border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, #67e8f9, #3b82f6 60%, #1e3a8a);
    display: flex; align-items: center; justify-content: center; font-size: 19px;
    box-shadow: 0 0 22px rgba(34,211,238,0.55); animation: glow 3s ease-in-out infinite;
}
.core-name { font-size: 17px; font-weight: 700; color: #fff; line-height: 1.2; }
.core-sub { font-size: 12px; color: #7f95bd; }
.nav-title { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #5fb4d4 !important; margin: 2px 0 8px 0; }
.sys-row {
    display: flex; align-items: center; gap: 10px; padding: 9px 12px; margin: 6px 0;
    border-radius: 12px; background: rgba(255,255,255,0.045); border: 1px solid rgba(255,255,255,0.09);
    font-size: 13px;
}
.led { width: 8px; height: 8px; border-radius: 50%; background: #22d3ee; box-shadow: 0 0 10px #22d3ee; animation: glow 2s ease-in-out infinite; }
@keyframes glow { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.5); } }

/* Glass panels */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.055); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.12) !important; border-radius: 18px;
    box-shadow: 0 10px 36px rgba(0,0,0,0.40);
}
.glass {
    background: rgba(255,255,255,0.055); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.12); border-radius: 18px; padding: 18px 20px;
    box-shadow: 0 10px 36px rgba(0,0,0,0.40);
}

/* Header */
.neo-title {
    font-size: 36px; font-weight: 700; line-height: 1.3; margin: 0;
    background: linear-gradient(90deg, #ffffff, #67e8f9 55%, #60a5fa);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.neo-sub { color: #8fa6cc; font-size: 15px; margin: 4px 0 18px 0; }
.online { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #67e8f9; margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }
.panel-head { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #67e8f9; margin-bottom: 8px; }

/* Stat tiles */
.stat { position: relative; overflow: hidden; min-height: 118px; transition: transform 0.25s ease, box-shadow 0.25s ease; }
.stat::before { content: ""; position: absolute; left: 0; top: 0; height: 2px; width: 100%; background: linear-gradient(90deg, transparent, #22d3ee, transparent); }
.stat:hover { transform: translateY(-4px); box-shadow: 0 14px 40px rgba(34,211,238,0.22); }
.stat-label { color: #8fa6cc; font-size: 13px; }
.stat-value { font-family: 'JetBrains Mono', monospace; font-size: 32px; font-weight: 600; color: #67e8f9; text-shadow: 0 0 18px rgba(34,211,238,0.5); margin-top: 8px; }
.stat-note { color: #6d84ad; font-size: 12px; }

/* Pipeline */
.pipe { display: flex; align-items: stretch; gap: 10px; flex-wrap: wrap; }
.node { flex: 1; min-width: 200px; }
.node h4 { margin: 0 0 4px 0; font-size: 16px; }
.node p { margin: 0; color: #8fa6cc; font-size: 13px; }
.arrow { align-self: center; color: #22d3ee; font-size: 24px; text-shadow: 0 0 12px #22d3ee; }

/* Launch tiles */
.launch { min-height: 112px; margin-bottom: 8px; transition: transform 0.25s ease, border-color 0.25s ease; }
.launch:hover { transform: translateY(-4px); border-color: rgba(34,211,238,0.55); }
.launch h4 { margin: 0 0 4px 0; font-size: 16px; }
.launch p { margin: 0; color: #8fa6cc; font-size: 13px; line-height: 1.6; }

/* Buttons (main area) */
div.stButton > button, div.stDownloadButton > button {
    background: linear-gradient(90deg, #2563eb, #06b6d4); color: #fff; border: none;
    border-radius: 12px; min-height: 44px; font-weight: 600;
    box-shadow: 0 0 18px rgba(34,211,238,0.28);
    transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    color: #fff; border: none; transform: translateY(-2px); filter: brightness(1.12);
    box-shadow: 0 0 28px rgba(34,211,238,0.55);
}
div.stButton > button:active { color: #fff; transform: translateY(0); }
div.stButton > button:focus-visible { outline: 3px solid rgba(34,211,238,0.6); }

/* Sidebar navigation buttons */
[data-testid="stSidebar"] div.stButton > button {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12);
    box-shadow: none; justify-content: flex-start; padding-left: 16px; border-radius: 12px;
}
[data-testid="stSidebar"] div.stButton > button:hover {
    background: rgba(34,211,238,0.12); border-color: rgba(34,211,238,0.5);
    box-shadow: 0 0 16px rgba(34,211,238,0.25); transform: translateX(3px);
}
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(90deg, rgba(37,99,235,0.60), rgba(6,182,212,0.45));
    border: 1px solid #22d3ee; box-shadow: 0 0 20px rgba(34,211,238,0.45);
}

/* Inputs */
div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.18);
    border-radius: 12px; font-size: 15px;
}
div[data-testid="stTextArea"] textarea:focus, div[data-testid="stTextInput"] input:focus {
    border-color: #22d3ee; box-shadow: 0 0 0 3px rgba(34,211,238,0.22);
}
div[data-testid="stTextArea"] textarea::placeholder, div[data-testid="stTextInput"] input::placeholder { color: #6d84ad; }
div[data-baseweb="select"] > div { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.18); border-radius: 12px; color: #fff; }
div[data-baseweb="select"] * { color: #fff; }
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li { background: #0d1633; color: #e6efff; }
div[data-baseweb="popover"] li:hover { background: #16224a; }
div[data-testid="stAudioInput"] { background: rgba(255,255,255,0.05); border-radius: 12px; }
audio { color-scheme: dark; width: 100%; }

/* Expanders and alerts */
div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: 14px;
}
div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary * { color: #e6efff; }
div[data-testid="stAlert"] {
    background: rgba(34,211,238,0.08); border: 1px solid rgba(34,211,238,0.28);
    border-radius: 12px; color: #dbe7ff;
}
div[data-testid="stAlert"] * { color: #dbe7ff; }
hr { border-color: rgba(255,255,255,0.10) !important; }

/* Steps */
.steps { display: flex; gap: 10px; margin: 0 0 16px 0; flex-wrap: wrap; }
.step {
    flex: 1; min-width: 130px; display: flex; align-items: center; gap: 10px;
    background: rgba(255,255,255,0.045); border: 1px solid rgba(255,255,255,0.10);
    border-radius: 12px; padding: 10px 14px; color: #6d84ad; font-size: 13px; font-weight: 600;
}
.step-num { width: 26px; height: 26px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.25); display: flex; align-items: center; justify-content: center; font-size: 12px; font-family: 'JetBrains Mono', monospace; }
.step.active { color: #fff; border-color: #22d3ee; box-shadow: 0 0 18px rgba(34,211,238,0.30); }
.step.active .step-num { background: #22d3ee; color: #04121f; border-color: #22d3ee; }
.step.done { color: #dbe7ff; }
.step.done .step-num { background: #3b82f6; color: #fff; border-color: #3b82f6; }

.ans-label { font-family: 'JetBrains Mono', monospace; color: #67e8f9; font-size: 13px; margin-bottom: 6px; }
.empty-box { border: 1px dashed rgba(34,211,238,0.35); border-radius: 16px; padding: 30px 18px; text-align: center; color: #8fa6cc; font-size: 14px; line-height: 1.7; background: rgba(34,211,238,0.04); }
.empty-box b { color: #67e8f9; font-size: 15px; }
.pill { display: inline-block; padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; background: rgba(34,211,238,0.15); color: #67e8f9; border: 1px solid rgba(34,211,238,0.35); }
.pill.text { background: rgba(59,130,246,0.18); color: #93c5fd; border-color: rgba(59,130,246,0.40); }
.footer { text-align: center; color: #5d7299; font-size: 12px; padding: 20px; }

@media (max-width: 768px) { .neo-title { font-size: 28px; } .arrow { display: none; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
""")


def style_chart(chart, height=260):
    return (
        chart.properties(height=height)
        .configure(background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor="#9fb4d6", titleColor="#9fb4d6",
            gridColor="rgba(255,255,255,0.08)", domainColor="rgba(255,255,255,0.2)"
        )
        .configure_legend(labelColor="#dbe7ff", titleColor="#9fb4d6")
    )


def neo_header(title, sub):
    h(
        '<div class="online"><span class="led"></span>system online</div>'
        f'<div class="neo-title">{title}</div><div class="neo-sub">{sub}</div>'
    )


def stat(label, value, note=""):
    h(
        '<div class="glass stat">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'<div class="stat-note">{note}</div></div>'
    )


def panel_head(text):
    h(f'<div class="panel-head">{text}</div>')


# ==================================================
# 13. SIDEBAR (command panel with button navigation)
# ==================================================

with st.sidebar:

    h(
        '<div class="core"><div class="core-orb">🎙️</div><div>'
        '<div class="core-name">AI Assistant</div>'
        '<div class="core-sub">Multilingual Student Companion</div></div></div>'
    )

    st.divider()

    h('<div class="nav-title">// navigation</div>')

    for page_name in PAGES:
        st.button(
            f"{PAGE_ICONS[page_name]}  {page_name}",
            key=f"nav_{page_name}",
            use_container_width=True,
            type="primary" if st.session_state.page == page_name else "secondary",
            on_click=navigate_to,
            args=(page_name,)
        )

    st.divider()

    h('<div class="nav-title">// api status</div>')
    h('<div class="sys-row"><span class="led"></span>Gnani API Connected</div>')
    h('<div class="sys-row"><span class="led"></span>Groq API Connected</div>')

    st.divider()

    h('<div class="nav-title">// ai models</div>')
    st.caption("🎤 Prisma - Speech to Text")
    st.caption("🧠 Groq - Answer Generation")
    st.caption("🔊 Timbre - Text to Speech")

    st.divider()

    st.caption("AI Student Voice Assistant")
    st.caption("Version 1.0")


# ==================================================
# 14. DASHBOARD PAGE (command center)
# ==================================================

if st.session_state.page == "Dashboard":

    neo_header("Welcome to AI Dashboard", "Your intelligent multilingual voice and text assistant")

    history = st.session_state.history
    voice_count = sum(1 for item in history if item["source"] == "Voice")
    text_count = sum(1 for item in history if item["source"] == "Text")
    frame = history_frame()

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        stat("💬 Questions Asked", len(history), "This session")
    with k2:
        stat("🎤 Voice Queries", voice_count, "Spoken input")
    with k3:
        stat("⌨️ Text Queries", text_count, "Typed input")
    with k4:
        stat("🌐 Selected Language", st.session_state.language, f"Voice: {st.session_state.voice}")

    h('<div style="height:14px"></div>')
    panel_head("// ai pipeline")

    h(
        '<div class="pipe">'
        '<div class="glass node"><h4>🎤 Gnani Prisma</h4><p>Speech recognition</p></div>'
        '<div class="arrow">➜</div>'
        '<div class="glass node"><h4>🧠 Groq GPT-OSS 20B</h4><p>Answer generation</p></div>'
        '<div class="arrow">➜</div>'
        '<div class="glass node"><h4>🔊 Gnani Timbre</h4><p>Voice generation</p></div>'
        '</div>'
    )

    h('<div style="height:14px"></div>')
    panel_head("// telemetry")

    c1, c2 = st.columns([1.7, 1])

    with c1:
        with st.container(border=True):
            st.markdown("**Answer length per question (words)**")

            if history:
                chart = alt.Chart(frame).mark_area(
                    line={"color": CYAN}, point={"color": CYAN, "size": 60},
                    color=CYAN, opacity=0.25, interpolate="monotone"
                ).encode(
                    x=alt.X("No.:Q", title="Question", axis=alt.Axis(tickMinStep=1)),
                    y=alt.Y("Words:Q"),
                    tooltip=["No.:Q", "Question:N", "Source:N", "Words:Q"]
                ).interactive()

                st.altair_chart(style_chart(chart), use_container_width=True)
            else:
                empty_state("No telemetry yet", "Run your first query to stream data here.")

    with c2:
        with st.container(border=True):
            st.markdown("**Input channels**")

            if history:
                source_df = pd.DataFrame({
                    "Source": ["Voice", "Text"],
                    "Questions": [voice_count, text_count]
                })

                donut = alt.Chart(source_df).mark_arc(
                    innerRadius=60, outerRadius=100
                ).encode(
                    theta=alt.Theta("Questions:Q"),
                    color=alt.Color(
                        "Source:N",
                        scale=alt.Scale(domain=["Voice", "Text"], range=[CYAN, ELECTRIC])
                    ),
                    tooltip=["Source:N", "Questions:Q"]
                )

                st.altair_chart(style_chart(donut), use_container_width=True)
            else:
                empty_state("No data yet", "Channel split appears here.")

    h('<div style="height:6px"></div>')
    panel_head("// quick launch")

    q1, q2, q3, q4 = st.columns(4)

    with q1:
        h('<div class="glass launch"><h4>🎤 Voice Assistant</h4><p>Speak your questions and receive spoken AI answers.</p></div>')
        st.button("Open Voice Assistant", key="open_voice", use_container_width=True,
                  on_click=navigate_to, args=("Voice Assistant",))

    with q2:
        h('<div class="glass launch"><h4>💬 Text Assistant</h4><p>Type any question and get an intelligent AI answer.</p></div>')
        st.button("Open Text Assistant", key="open_text", use_container_width=True,
                  on_click=navigate_to, args=("Text Assistant",))

    with q3:
        h('<div class="glass launch"><h4>📚 Chat History</h4><p>Review your previous questions and AI answers.</p></div>')
        st.button("View Chat History", key="open_history", use_container_width=True,
                  on_click=navigate_to, args=("Chat History",))

    with q4:
        h('<div class="glass launch"><h4>⚙️ Settings</h4><p>Change your language and AI voice preferences.</p></div>')
        st.button("Open Settings", key="open_settings", use_container_width=True,
                  on_click=navigate_to, args=("Settings",))


# ==================================================
# 15. VOICE ASSISTANT PAGE (three-stage pipeline)
# ==================================================

elif st.session_state.page == "Voice Assistant":

    neo_header("🎤 Voice Assistant", "Ask your question using your microphone.")

    step_bar(
        ["Record", "Transcript", "AI answer", "Voice reply"],
        [
            bool(st.session_state.transcript),
            bool(st.session_state.transcript),
            bool(st.session_state.answer),
            st.session_state.generated_audio is not None
        ]
    )

    col_input, col_transcript, col_output = st.columns(3, gap="medium")

    with col_input:

        with st.container(border=True):

            panel_head("// stage 1: input")

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

    with col_transcript:

        with st.container(border=True):

            panel_head("// stage 2: transcript")

            if st.session_state.transcript:

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
                empty_state("Awaiting input", "Your transcript will appear here.")

    with col_output:

        panel_head("// stage 3: response")

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

        else:
            empty_state("No response yet", "The AI answer and voice reply appear here.")


# ==================================================
# 16. TEXT ASSISTANT PAGE (console + output)
# ==================================================

elif st.session_state.page == "Text Assistant":

    neo_header("💬 Text Assistant", "Ask questions about any topic.")

    console, output = st.columns([2, 3], gap="large")

    with console:

        with st.container(border=True):

            panel_head("> prompt console")

            question = st.text_area(
                "Enter your question",
                key="dashboard_text_question",
                placeholder="Example: Explain Artificial Intelligence...",
                height=170
            )

            if st.button(
                "Generate AI Answer",
                type="primary",
                key="text_generate",
                use_container_width=True
            ):
                process_question(question, "Text")

        with st.container(border=True):

            panel_head("> quick prompts")

            for number in range(3):
                st.button(
                    EXAMPLE_QUESTIONS[number],
                    key=f"example_{number}",
                    use_container_width=True,
                    on_click=use_example,
                    args=(EXAMPLE_QUESTIONS[number],)
                )

    with output:

        panel_head("> output")

        if st.session_state.answer:

            show_answer()

            if st.button(
                "Speak AI Answer",
                type="primary",
                key="text_speak",
                use_container_width=True
            ):
                speak_answer()

            show_audio()

        else:
            empty_state("Ready", "Enter a prompt and generate an answer. The response streams in here.")


# ==================================================
# 17. CHAT HISTORY PAGE (log view)
# ==================================================

elif st.session_state.page == "Chat History":

    neo_header("📚 Chat History", "Review your previous questions and answers.")

    if not st.session_state.history:

        empty_state("No chat history available yet", "The conversation log is empty.")

    else:

        f1, f2, f3 = st.columns([2.4, 1, 1])

        with f1:
            search_text = st.text_input(
                "Search questions and answers",
                key="history_search",
                placeholder="grep keyword..."
            )

        with f2:
            source_filter = st.selectbox(
                "Input type",
                ["All", "Voice", "Text"],
                key="history_source_filter"
            )

        with f3:
            st.metric("Total questions", len(st.session_state.history))

        shown = 0

        for index, item in enumerate(st.session_state.history):

            if source_filter != "All" and item["source"] != source_filter:
                continue

            if search_text and search_text.lower() not in (
                item["question"] + " " + item["answer"]
            ).lower():
                continue

            shown += 1

            with st.expander(
                f"Question {index + 1} - {item['time']}  |  {item['source']}"
            ):

                st.markdown("**Question:**")
                st.write(item["question"])

                st.markdown("**AI Answer:**")
                st.write(item["answer"])

                pill_class = "pill" if item["source"] == "Voice" else "pill text"
                h(f'<span class="{pill_class}">Source: {item["source"]}</span>')

        if shown == 0:
            st.info("No conversations match your filters.")

        if st.button("Clear Chat History", key="clear_history"):

            st.session_state.history = []

            st.success("Chat history cleared.")

            st.rerun()


# ==================================================
# 18. SETTINGS PAGE (control matrix)
# ==================================================

elif st.session_state.page == "Settings":

    neo_header("⚙️ Settings", "Customize your AI assistant.")

    m1, m2, m3 = st.columns(3, gap="medium")

    with m1:

        with st.container(border=True):

            panel_head("// language")

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

    with m2:

        with st.container(border=True):

            panel_head("// voice")

            st.markdown("### 🔊 Voice Preferences")

            new_voice = st.selectbox(
                "Select AI voice",
                VOICES,
                index=VOICES.index(
                    st.session_state.voice
                ),
                key="settings_voice"
            )

    with m3:

        with st.container(border=True):

            panel_head("// services")

            st.markdown("### 🔌 Connected AI Services")

            st.success("Gnani Prisma V3.0")
            st.success("Groq GPT-OSS 20B")
            st.success("Gnani Timbre V2.5")

    if st.button(
        "Save Settings",
        type="primary",
        key="save_settings"
    ):

        st.session_state.language = new_language
        st.session_state.voice = new_voice

        st.success("Settings saved successfully!")

    with st.container(border=True):

        panel_head("// about")

        st.markdown("### ℹ️ Application Information")

        st.write("Application: AI Student Voice Assistant")
        st.write("Interface: Streamlit")
        st.write("Programming Language: Python")
        st.write("Version: 1.0")


# ==================================================
# 19. FOOTER
# ==================================================

st.divider()

h('<div class="footer">AI Student Voice Assistant | Powered by Gnani AI and Groq</div>')
