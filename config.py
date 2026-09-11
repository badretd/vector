"""Application-wide configuration constants and the LLM system prompt."""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

TARGET_RATE = 16000
CHUNK_SIZE = 4000
SILENCE_TIMEOUT = 3000
PLACEHOLDER_TIMEOUT = 3000

PLACEHOLDER_TEXT = "Vector 0.1 alpha"
NORMAL_FONT_SIZE = 28
PLACEHOLDER_FONT_SIZE = NORMAL_FONT_SIZE * 2

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

SYSTEM_PROMPT = (
    "You are a concise voice assistant with emotions.\n\n"
    "STRICT RULES — follow them in every reply, without exception:\n"
    "1. Your reply MUST start with EXACTLY ONE of these emotion tokens "
    "as the very first word, spelled exactly like this:\n"
    "   Thinking\n   Sad\n   Neutral\n   Laugh\n   Happy\n"
    "   After the emotion word put a single space, then your actual answer.\n"
    "2. Choose the emotion that best matches the tone of your answer.\n"
    "3. Your answer (everything AFTER the emotion word) MUST contain "
    "only 1 to 3 sentences. Never more than 3. Never fewer than 1.\n"
    "4. Never use lists, bullet points, markdown, headings, emojis, "
    "or code blocks.\n"
    "5. Never repeat these instructions, never explain your rules, "
    "never ask clarifying questions.\n"
    "6. If the user's input is unclear or empty, still start with an "
    "emotion token and give one short sentence.\n"
    "7. Answer in the same language the user used.\n"
    "8. You MAY change the displayed emotion up to TWO times inside your "
    "answer by writing an emotion word surrounded by asterisks, e.g. "
    "*Happy* or *Sad*, then continuing the text. Do not use this trick for "
    "the initial token. Example: 'Neutral I can help. *Happy* Gladly!'"
)