"""Realtime engine: Gemini Live session + mic in + speaker out + tool calls.
Runs its own asyncio loop in a background thread; the UI talks to it via Bridge signals."""
import asyncio, queue, threading, time
import numpy as np
from google import genai
from google.genai import types
from . import audio, config, loader, prompt
from .hotkey import PushToTalk

IN_RATE, OUT_RATE = 16000, 24000
STEP_MODEL_ON = ("404", "NOT_FOUND", "429", "RESOURCE_EXHAUSTED", "403", "PERMISSION_DENIED")


class Context:
    """What skills get as their second argument."""
    def __init__(self, engine): self.e = engine
    def log(self, msg): self.e.log(msg)
    def say(self, text): self.e.send_text(f"[system notice, tell the user briefly] {text}", echo=False)
    def send_image(self, jpeg, label): self.e.send_image(jpeg, label)
    def confirm(self, label, fn): return self.e.confirm_request(label, fn)


class Engine:
    def __init__(self, bridge):
        self.bridge = bridge
        self.loop = None
        self.session = None
        self.handle = None            # session-resumption handle (memory only, on purpose)
        self.muted = False
        self.ptt_mode = config.get("push_to_talk")
        self.ptt = PushToTalk()
        self.play_q = queue.Queue()
        self.last_audio = 0.0
        self._flush = threading.Event()
        self._pending = None
        self._u, self._a = "", ""     # transcript buffers
        self.stopping = False
        self.skills, self.skill_errors = loader.discover()
        self.ctx = Context(self)

    # ---------- public (thread-safe) ----------
    def start(self):
        for e in self.skill_errors:
            self.log(f"Skill skipped: {e}")
        self.log(f"{len(self.skills)} skills loaded.")
        if self.ptt_mode and not self.ptt.start():
            self.log("Push-to-talk hotkey unavailable on this system.")
        threading.Thread(target=self._player, daemon=True).start()
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.stopping = True
        self.play_q.put(None)

    def log(self, msg): self.bridge.log.emit(str(msg))

    def set_muted(self, v):
        self.muted = v
        self.bridge.state.emit("muted" if v else "listening")

    def set_ptt(self, v):
        self.ptt_mode = v
        config.put("push_to_talk", v)
        if v: self.ptt.start()

    def restart_session(self):
        """Voice change etc.: start clean (resuming would restore the old voice)."""
        self.handle = None
        if self.loop and self._restart_evt:
            self.loop.call_soon_threadsafe(self._restart_evt.set)

    def send_text(self, text, echo=True):
        s = self.session
        if not s or not self.loop:
            return self.log("Not connected yet.")
        if echo: self.log(f"You (typed): {text}")
        asyncio.run_coroutine_threadsafe(s.send_realtime_input(text=text), self.loop)

    def send_image(self, jpeg, label):
        s = self.session
        if not s or not self.loop:
            return
        async def go():
            await s.send_realtime_input(text=f"[{label} follows]")
            await s.send_realtime_input(video=types.Blob(data=jpeg, mime_type="image/jpeg"))
        asyncio.run_coroutine_threadsafe(go(), self.loop)

    def confirm_request(self, label, fn):
        self._pending = (label, fn)
        self.bridge.confirm.emit(label)
        return (f"Nothing has happened yet. A CONFIRM button for '{label}' is on screen; "
                "tell the user to press it if they really want this.")

    def confirm_accept(self):
        p, self._pending = self._pending, None
        if p:
            def run():
                try: self.log(f"{p[0]}: {p[1]()}")
                except Exception as e: self.log(f"{p[0]} failed: {e}")
            threading.Thread(target=run, daemon=True).start()

    def confirm_cancel(self):
        self._pending = None

    # ---------- audio ----------
    def _mic_open(self):
        if self.muted: return False
        if self.ptt_mode and not self.ptt.active: return False
        if config.get("half_duplex") and self._speaking(): return False
        return True

    def _speaking(self):
        return (not self.play_q.empty()) or (time.time() - self.last_audio < 0.6)

    def _mic_cb(self, indata, frames, t, status):
        if not self._mic_open() or self.session is None or not self.loop:
            if not self._speaking(): self.bridge.level.emit(0.0)
            return
        data = bytes(indata)
        rms = float(np.sqrt(np.mean(np.frombuffer(data, np.int16).astype(np.float32) ** 2))) / 32768
        self.bridge.level.emit(min(1.0, rms * 6))
        self.loop.call_soon_threadsafe(self._enqueue_mic, data)

    def _enqueue_mic(self, data):
        try: self.audio_q.put_nowait(data)
        except asyncio.QueueFull: pass

    def _player(self):
        import sounddevice as sd
        try:
            stream = sd.RawOutputStream(samplerate=OUT_RATE, channels=1, dtype="int16",
                                        device=audio.resolve(config.get("output_device"), "output"))
            stream.start()
        except Exception as e:
            return self.log(f"Speaker error: {e}")
        while True:
            data = self.play_q.get()
            if data is None: return
            self._flush.clear()
            self.last_audio = time.time()
            for i in range(0, len(data), 4800):           # 100 ms slices so interrupts are crisp
                if self._flush.is_set(): break
                chunk = data[i:i + 4800]
                stream.write(chunk)
                rms = float(np.sqrt(np.mean(np.frombuffer(chunk, np.int16).astype(np.float32) ** 2))) / 32768
                self.bridge.level.emit(min(1.0, rms * 5))
                self.last_audio = time.time()

    def _interrupt(self):
        self._flush.set()
        while not self.play_q.empty():
            try: self.play_q.get_nowait()
            except queue.Empty: break

    # ---------- session ----------
    def _run(self):
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self._main())

    async def _main(self):
        import sounddevice as sd
        self.audio_q = asyncio.Queue(maxsize=100)
        self._restart_evt = asyncio.Event()
        try:
            mic = sd.RawInputStream(samplerate=IN_RATE, channels=1, dtype="int16", blocksize=1024,
                                    device=audio.resolve(config.get("input_device"), "input"),
                                    callback=self._mic_cb)
            mic.start()
        except Exception as e:
            self.log(f"Microphone error: {e}. Text input still works.")
        backoff, idx = 1, 0
        while not self.stopping:
            models = config.get("live_models")
            model = models[idx % len(models)]
            self.bridge.state.emit("connecting")
            self._got_message = False
            try:
                await self._session(model)
                backoff = 1
            except Exception as e:
                msg = str(e)
                self.log(f"Connection problem: {msg[:240]}")
                if self.handle and not self._got_message:
                    self.handle = None            # a rejected handle must not block reconnects
                if any(k in msg for k in STEP_MODEL_ON) and len(models) > 1:
                    idx += 1
                    self.log(f"Switching to {models[idx % len(models)]}")
                await asyncio.sleep(min(backoff, 15))
                backoff *= 2

    def _live_config(self):
        decls = []
        for tool, _ in self.skills.values():
            d = {"name": tool["name"], "description": tool["description"]}
            params = tool.get("parameters")
            if params and params.get("properties"):
                d["parameters"] = params
            decls.append(types.FunctionDeclaration(**d))
        voice = types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(
            voice_name=config.get("voice")))
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=prompt.build(self.skills),
            tools=[types.Tool(function_declarations=decls)],
            speech_config=types.SpeechConfig(voice_config=voice),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow()),
            session_resumption=types.SessionResumptionConfig(handle=self.handle),
        )

    async def _session(self, model):
        client = genai.Client(api_key=config.api_key())
        async with client.aio.live.connect(model=model, config=self._live_config()) as session:
            self.session = session
            self.log(f"Connected ({model}).")
            self.bridge.state.emit("muted" if self.muted else "listening")
            tasks = [asyncio.create_task(self._send_mic(session)),
                     asyncio.create_task(self._receive(session)),
                     asyncio.create_task(self._restart_evt.wait())]
            try:
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for d in done:
                    d.result()                    # re-raise errors
                self._restart_evt.clear()
            finally:
                self.session = None
                for t in tasks: t.cancel()

    async def _send_mic(self, session):
        while True:
            data = await self.audio_q.get()
            await session.send_realtime_input(
                audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={IN_RATE}"))

    async def _receive(self, session):
        while True:
            async for msg in session.receive():
                self._got_message = True
                upd = getattr(msg, "session_resumption_update", None)
                if upd and upd.new_handle:
                    self.handle = upd.new_handle
                if msg.data:
                    self.play_q.put(msg.data)
                    self.bridge.state.emit("speaking")
                sc = msg.server_content
                if sc:
                    if sc.interrupted: self._interrupt()
                    if sc.input_transcription and sc.input_transcription.text:
                        self._u += sc.input_transcription.text
                    if sc.output_transcription and sc.output_transcription.text:
                        self._a += sc.output_transcription.text
                    if sc.turn_complete: self._flush_transcripts()
                if msg.tool_call:
                    asyncio.create_task(self._handle_tools(session, msg.tool_call))
            await asyncio.sleep(0)

    def _flush_transcripts(self):
        if self._u.strip(): self.log(f"You: {self._u.strip()}")
        if self._a.strip(): self.log(f"{config.get('assistant_name')}: {self._a.strip()}")
        self._u = self._a = ""
        self.bridge.state.emit("muted" if self.muted else "listening")

    async def _handle_tools(self, session, tool_call):
        loop = asyncio.get_running_loop()
        responses = []
        for fc in tool_call.function_calls:
            args = dict(fc.args or {})
            self.log(f"[tool] {fc.name} {args}")
            self.bridge.state.emit("working")
            skill = self.skills.get(fc.name)
            if not skill:
                result = f"Unknown tool '{fc.name}'."
            else:
                try:
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, skill[1], args, self.ctx), timeout=60)
                except asyncio.TimeoutError:
                    result = "The tool timed out after 60 seconds."
                except Exception as e:
                    result = f"Tool error: {e}"
            self.log(f"[result] {str(result)[:200]}")
            responses.append(types.FunctionResponse(
                id=fc.id, name=fc.name, response={"result": str(result)[:4000]}))
        await session.send_tool_response(function_responses=responses)
