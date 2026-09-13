"""Behavioural constants used by the application layer."""

# Silence before offering the "send" hint (ms).
SILENCE_TIMEOUT = 3000
# How long the placeholder stays visible on a fresh window (ms).
PLACEHOLDER_TIMEOUT = 3000
# How long the "press Enter" hint stays visible (ms).
SEND_HINT_TIMEOUT = 3000

# LLM sampling / request defaults.
LLM_TEMPERATURE = 0.6
LLM_REQUEST_TIMEOUT = 120.0
LLM_STOP_SEQUENCES = (
    "\nUser:", "\nuser:", "\nUSER:",
    "\nAssistant:", "\nassistant:", "\nASSISTANT:",
    "\nHuman:", "\nhuman:", "\nHUMAN:",
    "\nSystem:", "\nsystem:", "\nSYSTEM:",
)

# Ollama defaults (overridable via settings).
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_OLLAMA_MODEL = "phi3:3.8b-mini-4k-instruct-q4_K_M"

# Audio target rate (Vosk expects 16 kHz).
TARGET_AUDIO_RATE = 16000
AUDIO_CHUNK_SIZE = 4000