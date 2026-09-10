"""Application-wide configuration constants and the LLM system prompt."""

MODEL_PATH = "model"
TARGET_RATE = 16000
CHUNK_SIZE = 4000
SILENCE_TIMEOUT = 3000
PLACEHOLDER_TIMEOUT = 3000

PLACEHOLDER_TEXT = "Vector 0.0 alpha"
NORMAL_FONT_SIZE = 28
PLACEHOLDER_FONT_SIZE = NORMAL_FONT_SIZE * 2

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3:3.8b-mini-4k-instruct-q4_K_M"

STYLE_WHITE = "color: #ffffff; background-color: #000000; padding: 20px;"
STYLE_YELLOW = "color: #ffff00; background-color: #000000; padding: 20px;"

# Canonical emotion tokens the LLM is required to prefix its replies with.
EMOTIONS = ("Thinking", "Sad", "Neutral", "Laugh", "Happy")

EMOTIONS_DIR = "emotions"
EMOTION_SOURCE_SIZE = 12     # native pixel-art resolution
EMOTION_SCALE = 10           # nearest-neighbour upscale factor (no blur)
EMOTION_DISPLAY_SIZE = EMOTION_SOURCE_SIZE * EMOTION_SCALE

SYSTEM_PROMPT = (
    "You are a concise voice assistant with emotions.\n\n"
    "STRICT RULES — follow them in every reply, without exception:\n"
    "1. Your reply MUST start with EXACTLY ONE of these emotion tokens "
    "as the very first word, spelled exactly like this:\n"
    "   Thinking\n"
    "   Sad\n"
    "   Neutral\n"
    "   Laugh\n"
    "   Happy\n"
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
    "7. Answer in the same language the user used."
)