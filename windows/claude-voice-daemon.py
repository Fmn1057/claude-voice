#!/usr/bin/env python3
"""
Claude Voice Assistant — Windows daemon
- Alt+Z: primer press graba, segundo press envía a Claude
- Alt+Z mientras habla: interrumpe la voz
- Alt+X: para todo inmediatamente
"""

import sys
import os
from pathlib import Path

# ── Resolver proyecto y venv ──────────────────────────────────────────────────
_PROJECT = Path(__file__).resolve().parent.parent
_venv_site = _PROJECT / "venv" / "Lib" / "site-packages"
if _venv_site.exists():
    sys.path.insert(0, str(_venv_site))

import asyncio
import io
import json
import re
import signal
import socket
import subprocess
import tempfile
import threading
import time
import wave
from enum import Enum, auto

import keyboard          # pip install keyboard
import sounddevice as sd
from PIL import ImageGrab  # pip install pillow

# ── Configuración ─────────────────────────────────────────────────────────────

HOME        = Path.home()
TEMP        = Path(os.environ.get("TEMP", os.environ.get("TMP", "C:/Temp")))
VENV_EDGE   = _PROJECT / "venv" / "Scripts" / "edge-tts.exe"
LOGFILE     = TEMP / "claude-voice.log"
UI_SOCK     = TEMP / ".claude-voice.sock"

SAMPLE_RATE = 16000
FRAME_SIZE  = int(SAMPLE_RATE * 30 / 1000)   # 480 samples @ 30ms

MODEL_SIZE  = os.environ.get("CLAUDE_VOICE_MODEL", "small")
LANG        = os.environ.get("CLAUDE_VOICE_LANG", "es")
TTS_VOICE   = os.environ.get("CLAUDE_VOICE_TTS_VOICE", "es-MX-DaliaNeural")

SCREENSHOT_PATH = TEMP / "claude-voice-screenshot.png"


# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg: str):
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")


# ── UI overlay (socket) ───────────────────────────────────────────────────────

_ui_conn: socket.socket | None = None
_ui_lock = threading.Lock()


def ui_send(cmd: str, **kwargs):
    global _ui_conn
    msg = json.dumps({"cmd": cmd, **kwargs}) + "\n"
    with _ui_lock:
        if _ui_conn is None and UI_SOCK.exists():
            try:
                _ui_conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                _ui_conn.connect(str(UI_SOCK))
            except Exception as e:
                log(f"ui_connect error: {e}")
                _ui_conn = None
        if _ui_conn:
            try:
                _ui_conn.sendall(msg.encode())
            except Exception as e:
                log(f"ui_send error: {e}")
                _ui_conn = None


# ── Strip markdown ────────────────────────────────────────────────────────────

def strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\bSources?:.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\[[^\]]{0,80}\]", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^[\-=]{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}([^*\n]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_\n]+)_{1,3}", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", ". ", text)
    text = text.replace("\n", " ")
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


# ── TTS ───────────────────────────────────────────────────────────────────────

async def speak(text: str, stop: asyncio.Event):
    clean = strip_markdown(text)
    if not clean:
        return

    parts = re.split(r"(?<=[.!?])\s+", clean)
    parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 2]

    for part in parts:
        if stop.is_set():
            break
        tmp = Path(tempfile.mktemp(suffix=".mp3"))
        try:
            proc = await asyncio.create_subprocess_exec(
                str(VENV_EDGE), "--voice", TTS_VOICE,
                "--text", part, "--write-media", str(tmp),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()

            if stop.is_set() or not tmp.exists():
                break

            # Reproducir con mpv (Windows) o fallback a playsound
            player = _find_player()
            if player:
                mpv = await asyncio.create_subprocess_exec(
                    player, "--no-terminal", "--really-quiet", str(tmp),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                while mpv.returncode is None:
                    if stop.is_set():
                        mpv.kill()
                        await mpv.wait()
                        break
                    await asyncio.sleep(0.05)
            else:
                # Fallback: playsound
                await asyncio.get_event_loop().run_in_executor(
                    None, _playsound_fallback, str(tmp)
                )
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass


def _find_player() -> str | None:
    """Busca mpv en rutas comunes de Windows."""
    candidates = [
        "mpv",
        r"C:\Program Files\mpv\mpv.exe",
        r"C:\Program Files (x86)\mpv\mpv.exe",
        str(HOME / "scoop" / "apps" / "mpv" / "current" / "mpv.exe"),
        str(HOME / "AppData" / "Local" / "Programs" / "mpv" / "mpv.exe"),
    ]
    for c in candidates:
        try:
            r = subprocess.run([c, "--version"], capture_output=True, timeout=2)
            if r.returncode == 0:
                return c
        except Exception:
            pass
    return None


def _playsound_fallback(path: str):
    try:
        import playsound
        playsound.playsound(path)
    except Exception:
        # Último recurso: Windows Media Player vía PowerShell
        subprocess.run(
            ["powershell", "-c", f"(New-Object Media.SoundPlayer '{path}').PlaySync()"],
            capture_output=True
        )


# ── Grabación ─────────────────────────────────────────────────────────────────

def record_until_stop(stop: threading.Event) -> bytes | None:
    frames: list[bytes] = []
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="int16", blocksize=FRAME_SIZE) as stream:
            while not stop.is_set():
                chunk, _ = stream.read(FRAME_SIZE)
                frames.append(chunk.tobytes())
    except Exception as e:
        log(f"record error: {e}")
        return None

    if not frames:
        return None

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return buf.getvalue()


# ── Screenshot ────────────────────────────────────────────────────────────────

_VISION_KEYWORDS = {
    "pantalla", "screen", "ves", "ven", "veo", "qué hay", "que hay",
    "imagen", "dice", "muestra", "screenshot", "foto", "mira", "mirá",
    "look", "see", "qué ves", "que ves", "qué dice", "que dice",
    "qué aparece", "que aparece", "qué está", "que esta",
}

def needs_screenshot(text: str) -> bool:
    return any(k in text.lower() for k in _VISION_KEYWORDS)

def take_screenshot() -> bool:
    """Captura la pantalla completa con PIL (funciona en Windows sin dependencias extra)."""
    try:
        img = ImageGrab.grab(all_screens=True)
        img.save(str(SCREENSHOT_PATH))
        if SCREENSHOT_PATH.exists() and SCREENSHOT_PATH.stat().st_size > 5000:
            log("Screenshot OK (PIL ImageGrab)")
            return True
    except Exception as e:
        log(f"screenshot error: {e}")
    return False


# ── Transcripción ─────────────────────────────────────────────────────────────

_whisper_model = None

def transcribe(wav_bytes: bytes) -> str:
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        tmp = f.name
    try:
        segs, _ = _whisper_model.transcribe(tmp, language=LANG, vad_filter=True)
        return " ".join(s.text.strip() for s in segs).strip()
    finally:
        Path(tmp).unlink(missing_ok=True)


# ── Estado ────────────────────────────────────────────────────────────────────

class State(Enum):
    IDLE       = auto()
    RECORDING  = auto()
    PROCESSING = auto()
    SPEAKING   = auto()


# ── Asistente ─────────────────────────────────────────────────────────────────

class VoiceAssistant:
    def __init__(self):
        self.state          = State.IDLE
        self.stop_tts       = asyncio.Event()
        self.stop_rec       = threading.Event()
        self.trigger_q: asyncio.Queue = None
        self.loop: asyncio.AbstractEventLoop = None
        self._response_task: asyncio.Task | None = None

    # ── Hotkeys (keyboard library) ────────────────────────────────────────────

    def start_hotkey_listener(self):
        keyboard.add_hotkey("alt+z", self._on_alt_z, suppress=True)
        keyboard.add_hotkey("alt+x", self._on_alt_x, suppress=True)
        print("Hotkeys registrados: Alt+Z (grabar), Alt+X (parar)", flush=True)

    def _on_alt_z(self):
        if self.state == State.SPEAKING:
            self.loop.call_soon_threadsafe(self.stop_tts.set)
        else:
            asyncio.run_coroutine_threadsafe(
                self.trigger_q.put("toggle"), self.loop
            )

    def _on_alt_x(self):
        self.loop.call_soon_threadsafe(self._hard_stop_sync)

    def _hard_stop_sync(self):
        self.stop_tts.set()
        self.stop_rec.set()
        if self._response_task and not self._response_task.done():
            self._response_task.cancel()
        # Matar proceso Claude y reproductor de audio
        subprocess.Popen(
            ["taskkill", "/F", "/T", "/IM", "claude.exe"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        subprocess.Popen(
            ["taskkill", "/F", "/T", "/IM", "mpv.exe"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.state = State.IDLE
        ui_send("state", value="idle")
        ui_send("assistant_end")

    # ── Loop principal ────────────────────────────────────────────────────────

    async def run(self):
        from claude_agent_sdk import (
            ClaudeSDKClient, ClaudeAgentOptions,
            AssistantMessage, TextBlock, ResultMessage,
        )

        self.loop      = asyncio.get_running_loop()
        self.trigger_q = asyncio.Queue()

        self.start_hotkey_listener()

        SYSTEM_PROMPT = """Eres un asistente de voz que controla el escritorio Windows del usuario.

REGLAS CRÍTICAS:
- ACTÚA PRIMERO, explica después. Nunca planifiques en voz alta — simplemente ejecutá.
- Preferí SIEMPRE comandos PowerShell o CMD sobre navegar interfaces gráficas.
- Respuestas MUY cortas: máximo 1-2 oraciones después de actuar.
- Nunca uses markdown, listas, corchetes ni asteriscos.
- No digas lo que vas a hacer, hacelo y después confirmá brevemente.

CONTROL DEL ESCRITORIO — comandos disponibles vía Bash (PowerShell):
- Abrir apps: Start-Process "nombre.exe" o simplemente: firefox, notepad, code, steam, etc.
- Mouse: Add-Type y [System.Windows.Forms.Cursor]::Position o usar AutoHotkey
- Teclado: [System.Windows.Forms.SendKeys]::SendWait("texto")
- Portapapeles: Set-Clipboard "texto" / Get-Clipboard
- Notificaciones: [System.Windows.Forms.MessageBox]::Show("msg")
- Procesos: Stop-Process -Name "nombre" -Force
- Volumen: (Get-WmiObject -Class Win32_SoundDevice)
- Spotify: playerctl o Spotify URI spotify:track:xxx

CREAR ARCHIVOS:
- PowerShell: Set-Content, Out-File, New-Item
- Python: python -c "..." para scripts rápidos

CREAR PRESENTACIONES (PPT):
- python-pptx disponible: python -c "from pptx import Presentation; ..."

VER PANTALLA:
- Screenshot en: """ + str(SCREENSHOT_PATH) + """ — leélo con Read cuando pregunten qué hay en pantalla
- Si no podés verla, usá tu conocimiento o preguntá brevemente

SISTEMA:
- Instalar apps: winget install <paquete> o scoop install <paquete>
- Servicios: Start-Service / Stop-Service
- Admin: Start-Process powershell -Verb RunAs

El usuario habla en español. Responde SIEMPRE en español."""

        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            system_prompt=SYSTEM_PROMPT,
            model="claude-sonnet-4-6",
            cwd=HOME,
        )

        log("Cargando modelo Whisper...")
        await self.loop.run_in_executor(None, lambda: transcribe(
            b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
            b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        ))

        # Iniciar overlay UI
        ui_proc = subprocess.Popen(
            [sys.executable, str(_PROJECT / "windows" / "claude-voice-ui.py")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        await asyncio.sleep(1.5)

        first_start = True
        while True:
            try:
                async with ClaudeSDKClient(options=options) as client:
                    if first_start:
                        await speak("Sistema de voz listo", asyncio.Event())
                        first_start = False
                    ui_send("state", value="idle")
                    print("Listo. Alt+Z para hablar.", flush=True)

                    while True:
                        await self.trigger_q.get()

                        if self.state in (State.SPEAKING, State.PROCESSING):
                            continue

                        # Grabar
                        self.state = State.RECORDING
                        self.stop_rec.clear()
                        ui_send("state", value="recording")

                        rec_task = asyncio.ensure_future(
                            self.loop.run_in_executor(None, record_until_stop, self.stop_rec)
                        )
                        await self.trigger_q.get()
                        self.stop_rec.set()
                        wav = await rec_task

                        if not wav or len(wav) < 8000:
                            ui_send("state", value="idle")
                            self.state = State.IDLE
                            continue

                        # Transcribir
                        self.state = State.PROCESSING
                        ui_send("state", value="processing")
                        text = await self.loop.run_in_executor(None, transcribe, wav)
                        log(f"Transcripción: {text!r}")

                        if not text:
                            await speak("No entendí", asyncio.Event())
                            ui_send("state", value="idle")
                            self.state = State.IDLE
                            continue

                        ui_send("user", text=text)
                        claude_query = text
                        if needs_screenshot(text):
                            ok = await self.loop.run_in_executor(None, take_screenshot)
                            if ok:
                                claude_query = (
                                    f"{text}\n\n"
                                    f"[Screenshot disponible en {SCREENSHOT_PATH}. "
                                    f"Leélo con Read AHORA para responder.]"
                                )

                        # Claude
                        self.state = State.SPEAKING
                        self.stop_tts.clear()
                        ui_send("state", value="speaking")

                        try:
                            buf = {"full": "", "sent": ""}
                            ui_send("assistant_start")
                            await client.query(claude_query)

                            async def _recv():
                                interrupted = False
                                async for msg in client.receive_response():
                                    if self.stop_tts.is_set() and not interrupted:
                                        interrupted = True
                                        try:
                                            await client.interrupt()
                                        except Exception:
                                            pass
                                    if interrupted:
                                        continue
                                    if isinstance(msg, AssistantMessage):
                                        for block in msg.content:
                                            if isinstance(block, TextBlock):
                                                buf["full"] += block.text
                                                buf["sent"] += block.text
                                                ui_send("assistant_chunk", text=block.text)
                                                while re.search(r"[.!?]\s", buf["sent"]):
                                                    m = re.search(r"[.!?]\s", buf["sent"])
                                                    sentence = buf["sent"][:m.end()].strip()
                                                    buf["sent"] = buf["sent"][m.end():]
                                                    if sentence and not self.stop_tts.is_set():
                                                        await speak(sentence, self.stop_tts)

                            self._response_task = asyncio.ensure_future(_recv())
                            try:
                                await self._response_task
                            except asyncio.CancelledError:
                                log("Respuesta cancelada")
                            finally:
                                self._response_task = None

                            if buf["sent"].strip() and not self.stop_tts.is_set():
                                await speak(buf["sent"], self.stop_tts)
                            if not buf["full"].strip() and not self.stop_tts.is_set():
                                await speak("Listo", asyncio.Event())
                                ui_send("assistant_chunk", text="Listo.")

                            ui_send("assistant_end")
                            log(f"Respuesta: {buf['full'][:120]!r}")

                        except asyncio.CancelledError:
                            ui_send("assistant_end")
                        except Exception as e:
                            log(f"Claude SDK error: {e}")
                            ui_send("assistant_end")
                            killed = self.stop_tts.is_set()
                            if any(c in str(e) for c in ("143", "137", "exit code")):
                                if not killed:
                                    await speak("Sesión caída, reconectando", asyncio.Event())
                                raise
                            else:
                                await speak("Hubo un error, intentá de nuevo", asyncio.Event())

                        self.stop_tts.clear()
                        ui_send("state", value="idle")
                        self.state = State.IDLE

            except Exception as e:
                log(f"Sesión caída: {e} — reconectando en 2s")
                self.state = State.IDLE
                ui_send("state", value="idle")
                await asyncio.sleep(2)


# ── Entrada ───────────────────────────────────────────────────────────────────

async def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT,  lambda *_: sys.exit(0))
    print("Claude Voice Daemon (Windows) iniciando...", flush=True)
    await VoiceAssistant().run()


if __name__ == "__main__":
    asyncio.run(main())
