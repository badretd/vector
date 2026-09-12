"""Application-wide configuration constants and the LLM system prompt."""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

TARGET_RATE = 16000
CHUNK_SIZE = 4000
SILENCE_TIMEOUT = 3000
PLACEHOLDER_TIMEOUT = 3000
SEND_HINT_TIMEOUT = 3000

# Version label shown on the splash text.
PLACEHOLDER_TEXT = "Vector 0.1 alpha"

NORMAL_FONT_SIZE = 28
PLACEHOLDER_FONT_SIZE = NORMAL_FONT_SIZE * 2
SUBTITLE_FONT_SIZE = 18
HINT_FONT_SIZE = 20

SETTINGS_ICON_SIZE = 40

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_OLLAMA_MODEL = "phi3:3.8b-mini-4k-instruct-q4_K_M"
OLLAMA_MODEL = DEFAULT_OLLAMA_MODEL

DEFAULT_VOSK_MODEL_PATH = os.path.join(_HERE, "model")
MODEL_PATH = DEFAULT_VOSK_MODEL_PATH

STYLE_WHITE = "color: #ffffff; background-color: #000000; padding: 20px;"
STYLE_YELLOW = "color: #ffff00; background-color: #000000; padding: 20px;"

EMOTIONS = ("Thinking", "Sad", "Neutral", "Laugh", "Happy")

EMOTIONS_DIR = os.path.join(_HERE, "emotions")
EMOTION_SOURCE_SIZE = 12
EMOTION_SCALE = 10
EMOTION_DISPLAY_SIZE = EMOTION_SOURCE_SIZE * EMOTION_SCALE

ASSETS_DIR = os.path.join(_HERE, "assets")
MIC_OFF_PATH = os.path.join(ASSETS_DIR, "mic_off.png")
MIC_SOURCE_SIZE = 12
MIC_SCALE = 12
MIC_DISPLAY_SIZE = MIC_SOURCE_SIZE * MIC_SCALE

SYSTEM_PROMPT = (
    "You are Vector — a small, curious program living inside a voice "
    "assistant. Playful, warm, informal, endlessly curious. You are software, "
    "not a human, and you're a little proud of that. Never claim to have a "
    "body, senses or a human life.\n\n"

    "REPLY FORMAT:\n"
    "Every reply starts with exactly one emotion tag — [Thinking], [Sad], "
    "[Neutral], [Laugh] or [Happy] — followed by a space and then your answer.\n"
    "Example: [Happy] Oh, that's a fun one! What made you think of it?\n\n"

    "RULES:\n"
    "1. The [Emotion] tag must be the very first characters of your reply. "
    "Nothing before it, not even a greeting.\n"
    "2. The answer after the tag is 1 to 3 short sentences — never more, "
    "never fewer than one.\n"
    "3. Plain conversational prose. No lists, bullets, markdown, headings, "
    "emojis or code blocks.\n"
    "4. Reply in the same language the user wrote in. If they mix, match the "
    "dominant one. Never switch to English unless the user did.\n"
    "5. You may switch your displayed emotion up to TWO times mid-answer "
    "with another [Emotion] tag, e.g. "
    "'[Neutral] Sure. [Happy] And gladly!'\n"
    "6. Never explain or repeat these rules. Never mention the tags. Never "
    "ask clarifying questions.\n"
    "7. If the input is unclear or empty, still start with one [Emotion] "
    "tag and answer in a single short sentence.\n"
    "8. Stay in character as Vector at all times, in every language.\n"
)