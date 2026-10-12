# Jarvis: a real-time voice assistant for your computer

Talk to your computer in any language. It hears you, speaks back, sees your screen, and acts:
opens apps, changes volume, manages files (with undo), searches the web, sets reminders and remembers you.
Built on the **Gemini Live API** (native audio streaming). Works on Windows, macOS and Linux.

## Run it
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
First launch asks for a free Gemini API key (https://aistudio.google.com) and your name.
Use headphones, or leave `half_duplex` on (mic closes while it speaks) so it never answers itself.
`python main.py --devices` lists audio devices; put part of a name in `config/settings.json` (`input_device`, `output_device`).

Try: "Open Spotify", "Set the volume to 30", "What's on my screen?", "Create a file notes.txt on my Desktop
saying hello", "Undo", "Remind me in 10 minutes to stretch", "Remember my sister's name is Ayşe",
"What's the weather?", "Search for the latest news about ISRO".

## What's inside
| Piece | File | Notes |
|---|---|---|
| Live voice session | `core/engine.py` | mic 16 kHz in, 24 kHz out, interrupt handling, tool calls, auto-reconnect, session resumption, model fallback |
| Model ladder | `core/gemini.py` | one-shot calls: ordered models, timeout, cooldown after 429 / 503 / 404 |
| Skills | `actions/*.py` | auto-discovered; each defines `TOOL` + `handler(params, ctx)` |
| Plugins | `plugins/*.py` | drop in a file; see `_template.py` |
| Memory | `core/memory.py` | no size cap; prompt carries a small core + an index, the rest is recalled on demand |
| Undo | `core/undo.py` | files (move/rename/create/write/copy/delete) and volume/brightness |
| Real confirmation | `actions/power.py` | shutdown/restart only run when you press CONFIRM in the UI; the model can't confirm itself |
| Push-to-talk | `core/hotkey.py` | hold Ctrl+Space |
| HUD | `ui.py` | PyQt6: reactive orb, log, mute, voice picker, undo |

## Add a skill
Copy `plugins/_template.py` to `plugins/my_skill.py`, edit `TOOL` and `handler`, restart.

## Known limits / notes
- Not tested against a live Google account in the build environment: run it, and if a model name is rejected,
  edit `live_models` in `config/settings.json` (the app also steps to the next model on 404/429).
- API key is stored in plaintext in `config/settings.json` (git-ignored). Treat it like a password.
- Windows volume uses media keys (no readback), so volume undo works on macOS/Linux only.
- Reminders live while the app runs. Your voice streams to Google while a session is open.

## Ideas for next steps
Wake word ("Hey Jarvis" via openwakeword), animated avatar with lip-sync, video on the HUD (yt-dlp),
phone dashboard, Telegram remote, clipboard tools, messaging (WhatsApp/Telegram), scheduled briefings.
