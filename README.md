# Vector Voice

A desktop voice assistant with a small animated pixel-art face. Vector listens through your microphone, transcribes speech with Vosk, streams replies from a local LLM via Ollama, and reacts with emotions that change its on-screen avatar.

The assistant lives in a single frameless window: a centered sprite avatar, a text area at the bottom for your speech/typed input, a microphone indicator in the top-left corner, and a small settings menu in the top-right.

---

## Requirements

- **Python 3.10+** (the code uses `X | Y` union syntax and `dataclass` fields).
- **A working microphone.**
- **Ollama** running locally on `http://localhost:11434` (default).
- **A Vosk model archive** (a `.zip` produced by the Vosk project, e.g. `vosk-model-small-en-us-0.15.zip`) placed in the `data/` directory of the project.

### Python dependencies

The exact versions are pinned in `requirements.txt` at the project root. They include:

- `PyQt5` — desktop UI.
- `vosk` — speech recognition.
- `sounddevice` — microphone capture (PortAudio bindings).
- `numpy` — PCM handling.
- `scipy` — polyphase resampling.
- `requests` — HTTP client for Ollama.

Install everything with `pip install -r requirements.txt` (see below).

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/badretd/vector.git Friend
cd Friend
```

The directory is expected to be named `Friend` (the project root used by `bootstrap.py` is the parent of the `vector_voice/` package).

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

- **Linux / macOS**
  ```bash
  source .venv/bin/activate
  ```
- **Windows (PowerShell)**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows (cmd)**
  ```cmd
  .venv\Scripts\activate.bat
  ```

### 3. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Linux note:** `sounddevice` needs PortAudio at runtime. On Debian/Ubuntu:
> ```bash
> sudo apt install libportaudio2 portaudio19-dev
> ```
> On Fedora: `sudo dnf install portaudio`. On Arch: `sudo pacman -S portaudio`.

> **macOS note:** PortAudio is bundled with the `sounddevice` wheel; no extra steps are needed.

> **Windows note:** the `sounddevice` wheel ships with PortAudio; no extra steps are needed.

### 4. Install and start Ollama

Download Ollama from <https://ollama.com/download> and install it for your platform.

Then make sure the daemon is running. On Linux the installer usually registers a systemd service. On macOS and Windows the Ollama app starts automatically on login.

Verify:

```bash
curl http://localhost:11434/api/tags
```

You should receive a JSON response. If not, start Ollama manually with `ollama serve`.

### 5. Pull an LLM model

The default model in the app is:

```
phi3:3.8b-mini-4k-instruct-q4_K_M
```

Pull it (or any other model you prefer):

```bash
ollama pull phi3:3.8b-mini-4k-instruct-q4_K_M
```

Smaller models (e.g. `phi3:mini`, `llama3.2:3b`, `qwen2.5:3b`) are recommended for low-end machines.

### 6. Provide a Vosk speech model

Download a Vosk model archive from <https://alphacephei.com/vosk/models>. A good small English model is `vosk-model-small-en-us-0.15`.

Create a `data/` directory in the project root and drop the archive there:

```bash
mkdir -p data
mv ~/Downloads/vosk-model-small-en-us-0.15.zip data/
```

The first time the app runs, the setup wizard will offer to extract it into `model/`. You do **not** need to unzip it manually.

---

## Running the App

From the project root, with the virtual environment activated:

```bash
python main.py
```

Or, equivalently:

```bash
python -m vector_voice
```

---

## First-Time Setup Wizard

On the very first launch (when `setup_complete` is `False` in the settings), the app runs a short wizard:

1. **Language** — choose `English` or `Русский`. The choice is persisted and used for all subsequent UI strings.
2. **Vosk model** — if `model/` is empty, the wizard lists any `vosk-model-*.zip` archives in `data/` and extracts the one you pick. If no archive is present, it shows an error and continues (the app will not be able to recognize speech until you provide one).
3. **Ollama** — checks whether the Ollama daemon is reachable at `http://localhost:11434`. If not, it shows instructions and offers to retry. If it is reachable, it lists installed models and asks you to pick one.
4. **Microphone** — lists input devices, asks you to pick one, and asks whether to remember the choice.

If you chose "remember the microphone", subsequent launches will silently reuse the saved device as long as it is still present. If it disappeared (e.g. a USB mic was unplugged), the app re-prompts with the device picker — this time without touching the `remember_mic` flag.

---

## Features

- **Local speech recognition** with [Vosk](https://alphacephei.com/vosk/) (16 kHz, mono).
- **Local LLM streaming** via [Ollama](https://ollama.com) — no cloud required.
- **Animated emotion avatar** driven by inline `[Emotion]` tags the LLM is prompted to produce. Supported emotions: `Thinking`, `Sad`, `Neutral`, `Laugh`, `Happy`.
- **Bilingual UI** (English / Russian), switchable at first launch.
- **Two send modes**: press `Enter`, or auto-send after 3 seconds of silence.
- **Microphone selection** with an optional "remember my choice" flag.
- **Live zoom** with `Ctrl + scroll` (UI scale) and plain `scroll` (face scale).
- **Factory reset utility** (`reset_app.py`) that can wipe settings, logs, and the extracted Vosk model.
- **Clean architecture**: the domain layer is pure Python; Qt, `requests`, `sounddevice`, `vosk`, and `scipy` are confined to the infrastructure and presentation layers.

---

## How It Works

At a high level the app is a pipeline of four stages:

1. **Audio capture** — `SounddeviceAudioAdapter` enumerates input devices and picks a supported sample rate (prefers 16 kHz, otherwise falls back to the device default). `VoskSpeechAdapter` spawns a `QThread` (`_SpeechWorker`) that opens a `RawInputStream` and pushes raw int16 PCM chunks into a queue. If the device rate is not 16 kHz, the worker resamples with `scipy.signal.resample_poly` before feeding Vosk.

2. **Speech recognition** — Vosk's `KaldiRecognizer` receives audio in the worker thread. Partial and final hypotheses are emitted through a Qt signal. `SpeechService` forwards them to whoever registered via `on_text`.

3. **LLM streaming** — When the user submits a prompt, `ConversationService` sends a `SYSTEM_PROMPT` plus the user message to the currently selected Ollama model. `OllamaProvider` spawns another `QThread` (`_OllamaWorker`) that opens a streaming HTTP request and emits `chunk_ready` for every token.

4. **Emotion parsing and UI updates** — `EmotionParser` is an incremental stream parser. It reads the leading `[Emotion]` tag, then scans for up to two more inline tags. Visible text is forwarded to the UI; emotions are forwarded to the avatar. Unknown bracketed words like `[something]` are kept in the visible text so they are not eaten by mistake.

`MainWindowController` is the glue: it owns the timers (silence, placeholder, hint), translates UI events into service calls, and pushes results into `MainViewModel`. `VoiceWindow` subscribes to the view model's signals and re-renders widgets. **The view never calls a service directly** — it always goes through the controller, and the controller never touches widgets.

---

## Architecture

The project follows a **clean architecture** with four layers. The dependency direction is always inward: *presentation → application → domain*, with *infrastructure* implementing domain ports and being wired in `bootstrap.py`.

```
vector_voice/
├── domain/          # Pure data types + abstract ports. No external imports.
├── application/     # Use cases and services. Depends only on domain.
├── infrastructure/  # Concrete adapters (Vosk, Ollama, sounddevice, JSON, Qt assets).
├── presentation/    # PyQt5 widgets, view models, controllers.
└── bootstrap.py     # Composition root — builds everything and wires the app.
```

### Domain layer

- `models.py` — `Emotion`, `Language`, `SendMode`, `MessageRole`, `Message`, `MicrophoneInfo`, `AppSettings`.
- `events.py` — immutable event dataclasses (`SpeechRecognized`, `LlmChunkReceived`, `LlmFinished`, …).
- `ports.py` — abstract interfaces (`EventBusPort`, `SettingsRepositoryPort`, `SpeechRecognizerPort`, `LlmProviderPort`, `AudioDevicePort`, `VoskModelInstallerPort`, `AssetRepositoryPort`, `TranslationServicePort`, `ThemeManagerPort`).

Ports that are implemented by `QObject` subclasses (`SpeechRecognizerPort`, `LlmProviderPort`, `AvatarRendererPort`) are declared as `typing.Protocol` because `QObject` cannot coexist with `ABCMeta`.

### Application layer

- `services/conversation_service.py` — wraps an LLM provider and drives `EmotionParser`.
- `services/settings_service.py` — typed access to `AppSettings` with event-bus notification on change.
- `services/setup_service.py` — first-run flow: language → Vosk model → Ollama → microphone.
- `services/speech_service.py` — owns the recognizer lifecycle and an enable/disable flag.
- `emotion_parser.py` — the stream parser described above.
- `prompts.py` — the single `SYSTEM_PROMPT` used to keep the assistant in character.
- `constants.py` — timeouts, LLM defaults, audio constants.

### Infrastructure layer

- `speech_adapter.py` — Vosk + `sounddevice` + `QThread`.
- `llm/ollama.py` — streaming Ollama provider on a `QThread`.
- `llm/registry.py` — provider registry so alternative backends can be plugged in.
- `audio_adapter.py` — device enumeration and sample-rate negotiation.
- `settings_repository.py` — JSON file in the user config directory.
- `asset_repository.py` — loads emotion sprites, the mic icon, and renders the settings hamburger icon.
- `translation_service.py` — dictionary-based RU/EN translator.
- `vosk_installer.py` — extracts a bundled Vosk zip into `model/`.
- `event_bus.py`, `http_client.py` — supporting utilities.

### Presentation layer

- `qt/app.py` — `QApplication` factory.
- `qt/viewmodel.py` — `MainViewModel`, a pure `QObject` with `pyqtSignal` notifications.
- `qt/controller.py` — `MainWindowController`, the orchestrator.
- `qt/main_window.py` — the main `QWidget`: avatar, text stack, mic icon, settings menu.
- `qt/avatar_widget.py` — `SpriteAvatarWidget` (nearest-neighbour scaled sprite).
- `qt/widgets.py` — `ClickableLabel`, `EditableTextEdit`.
- `qt/theme.py` — theme tokens (currently a single dark palette).
- `qt/setup_wizard.py` — `QtSetupView` implementing the `SetupView` protocol.

---

## Usage

### Voice input

Just speak. The microphone is active by default. Vosk streams partial hypotheses into the text area; the final hypothesis replaces the partial text.

If **Send mode = Enter** (default):
- After 3 seconds of silence, a hint appears: *"Press Enter to send the text"*.
- Press `Enter` (or click the response label after a reply) to submit.

If **Send mode = Timer**:
- After 3 seconds of silence, the prompt is sent automatically.

### Typed input

You can type directly into the text area at any time. Typing suppresses the silence timer and hides the hint. When you edit text manually, Vosk's partial results are appended as a delta on top of your edits instead of overwriting them — you keep full control of the text.

### Send modes

Switch between the two modes from the **settings menu** (top-right hamburger icon, only visible while the microphone is muted).

When you start typing manually while in *Timer* mode, the app temporarily reverts to *Enter* mode for that message and restores *Timer* mode after sending.

### Zoom

- **`Ctrl + scroll`** — zoom the whole UI (from 0.6× to 2.4×).
- **`scroll`** — zoom the avatar only (from 0.4× to 8×).

### Microphone toggle

**Left-click anywhere on the window** (except on the response label) to toggle the microphone. When muted, the mic-off icon appears in the top-left corner and the settings menu in the top-right becomes visible.

Clicking the **response label** while a reply is visible clears it and returns you to input mode. Clicking while the LLM is still generating cancels the generation.

### Settings menu

The hamburger menu in the top-right (visible while muted) currently exposes:

- **Send mode** — *Send by Enter* or *Send by timer (3 sec)*.

Both options are saved to disk immediately.

---

## Configuration and Data Locations

User settings live in a platform-specific directory:

| Platform | Path |
|---|---|
| Linux / BSD | `$XDG_CONFIG_HOME/vector_voice/settings.json` or `~/.config/vector_voice/settings.json` |
| macOS | `~/.config/vector_voice/settings.json` |
| Windows | `%APPDATA%\vector_voice\settings.json` |

The file is a small JSON document with the following keys (all optional, defaults are applied on load):

```json
{
  "language": "en",
  "mic_device_index": 3,
  "mic_device_name": "Built-in Microphone",
  "remember_mic": true,
  "vosk_model_dir": "model",
  "ollama_model": "phi3:3.8b-mini-4k-instruct-q4_K_M",
  "setup_complete": true,
  "send_mode": "enter",
  "llm_provider": "ollama",
  "proxy_url": null,
  "theme_id": "default_dark"
}
```

`llm_provider`, `proxy_url`, and `theme_id` are placeholders for planned features and are not wired to the UI yet.

The extracted Vosk model lives in `model/` in the project root. Log files (when present) are written next to `main.py`.

---

## Project Layout

```
Friend/
├── main.py                          # Entry point
├── reset_app.py                     # Factory reset utility
├── scan.py                          # Project map generator (dev tool)
├── requirements.txt
├── README.md
├── assets/                          # mic_off.png and other UI assets
├── emotions/                        # Happy.png, Sad.png, Thinking.png, ...
├── data/                            # vosk-model-*.zip archives (input)
├── model/                           # Extracted Vosk model (output)
└── vector_voice/
    ├── __init__.py
    ├── __main__.py
    ├── bootstrap.py
    ├── application/
    │   ├── constants.py
    │   ├── emotion_parser.py
    │   ├── prompts.py
    │   └── services/
    │       ├── conversation_service.py
    │       ├── settings_service.py
    │       ├── setup_service.py
    │       └── speech_service.py
    ├── domain/
    │   ├── events.py
    │   ├── models.py
    │   └── ports.py
    ├── infrastructure/
    │   ├── asset_repository.py
    │   ├── audio_adapter.py
    │   ├── event_bus.py
    │   ├── http_client.py
    │   ├── settings_repository.py
    │   ├── speech_adapter.py
    │   ├── translation_service.py
    │   ├── vosk_installer.py
    │   └── llm/
    │       ├── ollama.py
    │       └── registry.py
    └── presentation/
        └── qt/
            ├── app.py
            ├── avatar_widget.py
            ├── controller.py
            ├── main_window.py
            ├── setup_wizard.py
            ├── theme.py
            ├── viewmodel.py
            └── widgets.py
```

---

## Resetting the App

`reset_app.py` wipes the user settings file and optionally the extracted Vosk model and log files. It uses only the standard library, so it works even if the package's dependencies are broken.

```bash
python reset_app.py                    # delete settings.json only
python reset_app.py --wipe-vosk-model  # also delete model/
python reset_app.py --wipe-logs        # also delete *.log
python reset_app.py --all              # settings + model + logs
python reset_app.py --all -y           # skip confirmation
python reset_app.py --all -n           # dry-run, print only
python reset_app.py --keep-settings --wipe-logs
```

Useful flags:

| Flag | Effect |
|---|---|
| `--wipe-vosk-model` | Delete the extracted `model/` directory. |
| `--wipe-logs` | Delete `*.log` files in the project root. |
| `--all` | Same as `--wipe-vosk-model --wipe-logs`. |
| `-y`, `--yes` | Do not ask for confirmation. |
| `-n`, `--dry-run` | Only print what would be deleted. |
| `--keep-settings` | Keep `settings.json`; only wipe the model/logs. |

After a full reset, the next launch will show the first-time setup wizard again.

---

## Troubleshooting

**"Ollama is not running" during setup**
- Confirm the daemon is up: `curl http://localhost:11434/api/tags`.
- On Linux, `systemctl status ollama` (or `systemctl --user status ollama`).
- On macOS/Windows, open the Ollama app from the menu bar / system tray.

**"No Ollama models found"**
- Run `ollama pull <model>` and then retry. The model list is fetched from `/api/tags` on every check.

**"No input devices found"**
- Check that your OS sees the microphone (`arecord -l` on Linux, Sound settings on Windows/macOS).
- On Linux, ensure PortAudio is installed.
- If the device is busy, close other apps that may be holding it (browsers, Discord, OBS, …).

**Vosk model fails to load**
- Look for a `Failed to load Vosk model: ...` message on the console.
- Verify `model/` contains `am/`, `conf/`, and `graph/` subdirectories (or the model root directly). If extraction failed, delete `model/` and re-run the wizard.

**The assistant replies in the wrong language**
- The system prompt instructs the LLM to reply in the user's dominant language. Small models sometimes drift. Try a larger model or explicitly tell the assistant which language you prefer.

**Emotion tags leak into the visible text**
- The `EmotionParser` tolerates a set of common misspellings (`netral`, `hapy`, `lough`, …). If you see raw `[Happy]` inside a reply, the model produced a bracket shape the parser could not classify. Check the `_ALIASES` table in `application/emotion_parser.py`.

**High CPU usage / slow responses**
- Use a smaller Ollama model (`phi3:mini`, `qwen2.5:3b`).
- Use a small Vosk model (the `small` variants are 40–50 MB, the `big` ones are several GB).
- Lower the Ollama context length if you are running on a machine with little RAM.

---

## Extending the Project

The architecture is deliberately pluggable. A few natural extension points:

- **Add an LLM backend** — implement `LlmProviderPort` (a `QObject` with a `provider_id`, `is_available`, `list_models`, `stream_chat`, and `cancel`), register it in `LlmProviderRegistry`, and select it via `settings.llm_provider` in `bootstrap.py`.
- **Add a theme** — subclass or replace `ThemeTokens` in `presentation/qt/theme.py` and expose it through `QtThemeManager`. The token dataclass already separates colors, fonts, and asset sizes.
- **Add a vector avatar** — implement `AvatarRendererPort` (`widget`, `set_emotion`, `set_scale`, `refresh`) and swap it in for `SpriteAvatarWidget` in `VoiceWindow`.
- **Add a language** — extend `TEXTS` in `infrastructure/translation_service.py` and add the code to the `Language` enum.
- **Add a send trigger** — the silence timer lives in `MainWindowController`; the mode itself is a value on `SendMode`. Adding a new one is a matter of a new enum value and a branch in `_on_silence`.

---

## License

MIT License