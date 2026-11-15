import os
from dotenv import load_dotenv
from gnani.tts import GnaniTTSClient, AudioConfig

load_dotenv()

client = GnaniTTSClient(
    api_key=os.getenv("GNANI_API_KEY")
)

try:
    print("Testing Gnani Timbre...")

    audio = client.synthesize(
        "Hello! Welcome to AI Student Voice Assistant.",
        voice="Kaveri",
        model="timbre-v2.5",
        language="en-IN",
        speed=1.0,
        audio_config=AudioConfig(
            sample_rate=48000,
            encoding="linear_pcm",
            container="wav"
        )
    )

    with open("test_voice.wav", "wb") as file:
        file.write(audio)

    print("SUCCESS! Audio saved as test_voice.wav")

except Exception as error:
    print("TTS ERROR:", error)