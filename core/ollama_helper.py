"""Small helpers to detect and query a locally running Ollama server."""
import requests

from config import OLLAMA_URL

OLLAMA_BASE = OLLAMA_URL.rsplit("/api", 1)[0]
TAGS_URL = OLLAMA_BASE + "/api/tags"


def is_ollama_running(timeout: float = 1.5) -> bool:
    try:
        r = requests.get(TAGS_URL, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def list_ollama_models(timeout: float = 4.0):
    try:
        r = requests.get(TAGS_URL, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return sorted(m["name"] for m in data.get("models", []))
    except Exception:
        return []