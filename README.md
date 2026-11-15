# 🎙️ AI Student Voice Assistant

A multilingual voice and text study assistant built with **Streamlit**. Ask a question by speaking or typing, get a clear AI answer, and listen to it read back in your chosen voice.

- 🎤 **Speech to text:** Gnani Prisma (`prisma-v3.0`)
- 🧠 **Answer generation:** Groq `openai/gpt-oss-20b`
- 🔊 **Text to speech:** Gnani Timbre (`timbre-v2.5`)

---

## ✨ Features

| Page | What it does |
|---|---|
| **Dashboard** | KPI cards, usage charts, and shortcuts to every page |
| **Voice Assistant** | Record your question, convert it to text, generate an answer, and play it as speech |
| **Text Assistant** | Type a question, get an AI answer, and optionally hear it spoken |
| **Chat History** | Review, search, and clear previous questions and answers |
| **Settings** | Choose the language and the AI voice |

**Also included**

- 10 language options: Auto Detect, English, Telugu, Hindi, Tamil, Kannada, Malayalam, Marathi, Bengali, Gujarati
- 4 voices: Kaveri, Nalini, Asmita, Suhana
- Download the spoken answer as a `.wav` file
- Automatic retry if speech generation fails once

---

## 🔄 How it works

```
Microphone ──► Gnani Prisma (STT) ──► Transcript
                                          │
Typed text ───────────────────────────────┤
                                          ▼
                              Groq GPT-OSS 20B ──► AI answer
                                                      │
                                                      ▼
                                        Gnani Timbre (TTS) ──► Audio (.wav)
```

---

## 🛠️ Tech stack

Python · Streamlit · Groq API · Gnani AI (STT and TTS) · python-dotenv · pandas · Altair

---

## 📁 Project structure

If you are publishing all three UI designs:

```
ai_voice_assistant_projects/
├── version1_corporate/     # Navy and white corporate dashboard
│   ├── app.py
│   ├── requirements.txt
│   └── .env.example
├── version2_creative/      # Purple and lavender creative dashboard
│   ├── app.py
│   ├── requirements.txt
│   └── .env.example
├── version3_futuristic/    # Dark glassmorphism AI dashboard
│   ├── app.py
│   ├── requirements.txt
│   └── .env.example
└── README.md
```

All three versions share the **same backend, features, and API integrations**. Only the UI and layout differ.

If you are publishing a single version, keep one folder with `app.py`, `requirements.txt`, and `.env.example`.

---

## 🚀 Getting started

### 1. Prerequisites

- Python 3.10 or newer
- A [Groq API key](https://console.groq.com/)
- A Gnani AI API key

### 2. Clone the repository

```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
```

### 3. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 4. Install dependencies

```bash
cd version1_corporate      # or version2_creative / version3_futuristic
pip install -r requirements.txt
```

> Also install the **Gnani SDK** package that provides `gnani.stt` and `gnani.tts`. Add its exact package name to `requirements.txt`.

### 5. Add your API keys

Copy the example file and fill in your keys:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

```env
GNANI_API_KEY=your_gnani_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

> 🔒 Never commit your real `.env` file. Add it to `.gitignore`.

### 6. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`. To run another version at the same time, use a different port:

```bash
streamlit run app.py --server.port 8502
```

---

## 🧭 Usage

**Voice Assistant**
1. Open **Voice Assistant** and record your question.
2. Click **Convert Speech to Text**.
3. Click **Generate AI Answer**.
4. Click **Speak AI Answer** to hear it, then download the audio if you like.

**Text Assistant**
1. Type a question, or pick one of the example prompts.
2. Click **Generate AI Answer**.
3. Click **Speak AI Answer** to listen.

**Settings:** pick your language and voice, then click **Save Settings**.

---

## ⚠️ Notes and limitations

- Chat history is stored in the Streamlit session, so it resets when the page is refreshed.
- Speech generation uses the first 800 characters of the answer.
- The language chosen in Settings is also used for speech recognition. Choose **Auto Detect** if you speak several languages.
- Requires Streamlit 1.40 or newer (for `st.audio_input`).

---

## 🖼️ Screenshots

Add your screenshots here:

| Dashboard | Voice Assistant |
|---|---|
| ![Dashboard](screenshots/dashboard.png) | ![Voice](screenshots/voice.png) |

---

## 🔧 Troubleshooting

| Problem | Fix |
|---|---|
| "API key is missing" message | Check that `.env` exists in the same folder as `app.py` and has both keys |
| `ModuleNotFoundError: gnani` | Install the Gnani SDK in your active virtual environment |
| Microphone widget not showing | Upgrade Streamlit: `pip install -U streamlit` |
| Speech not recognised | Select the correct language in Settings, or use Auto Detect |

---

## 👩‍💻 Author

Built by **Anumandla Vaishnavi**.

## 📄 License

Add a license of your choice (for example MIT) by creating a `LICENSE` file.
