# Claude Voice

Asistente de voz para **Linux y Windows** que controla el escritorio completo usando Claude AI. Activado con **Alt+Z**, transcribe tu voz con Whisper, la envía a Claude con acceso total al sistema, y responde por voz con síntesis de audio neural.

![Linux](https://img.shields.io/badge/Linux-KDE_Plasma_6-blue) ![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D4?logo=windows) ![Python](https://img.shields.io/badge/Python-3.11+-green) ![Claude](https://img.shields.io/badge/Claude-Sonnet_4-orange)

## ⚠️ Importante antes de usar

> **Esta aplicación le da a Claude acceso total a tu computador.** Antes de instalarla, ten en cuenta lo siguiente:

- **Claude Code CLI con sesión activa** — necesitas tener [Claude Code](https://claude.ai/download) instalado y haber iniciado sesión. La aplicación usa tu cuenta para procesar cada consulta, lo que **consume créditos o tokens** según tu plan de Anthropic.

- **Acceso completo al sistema** — Claude puede leer archivos, ejecutar comandos, instalar software, mover el mouse y presionar teclas. Esto es intencional para que pueda controlar el escritorio, pero significa que **no debes usarlo en un computador con información sensible** a menos que confíes completamente en lo que le vas a pedir.

- **Acceso al micrófono** — la aplicación graba audio cada vez que presionas Alt+Z. La transcripción se hace **localmente** con Whisper (sin internet), pero el texto transcrito sí se envía a los servidores de Anthropic para generar la respuesta.

- **Acceso a dispositivos de entrada (Linux)** — para capturar el atajo Alt+Z globalmente, el daemon lee directamente los dispositivos de teclado. Puede ser necesario agregar tu usuario al grupo `input`:
  ```bash
  sudo usermod -aG input $USER
  # Cerrar sesión y volver a entrar para que tome efecto
  ```

- **No es oficial de Anthropic** — este es un proyecto personal e independiente, no tiene afiliación con Anthropic.

## Características

- **Alt+Z** — primer press graba, segundo press transcribe y responde
- **Alt+Z** (mientras habla) — interrumpe la voz inmediatamente
- **Alt+X** — para todo (grabación, respuesta, TTS) en el instante
- Overlay flotante en la esquina inferior izquierda con la conversación en streaming
- Transcripción local con **faster-whisper** (sin internet, sin costo)
- Voz neural en español con **edge-tts** (Microsoft Neural, es-MX-DaliaNeural)
- Sesión persistente multi-turno con **Claude Agent SDK**
- Captura de pantalla automática cuando le preguntas sobre lo que ves
- Control total del escritorio: mouse, teclado, ventanas, apps, archivos
- Instala apps, crea documentos, controla Spotify, y más

## Requisitos

|  | Linux | Windows |
|--|-------|---------|
| **SO** | CachyOS / Arch Linux | Windows 10/11 (64-bit) |
| **Entorno** | KDE Plasma 6 + Wayland | — |
| **Python** | 3.11+ | 3.11+ |
| **Claude CLI** | ✓ | ✓ |

## Instalación

### 🐧 Linux (Arch / CachyOS)

```bash
# 1. Dependencias del sistema
sudo pacman -S python python-pip python-faster-whisper python-evdev \
               python-pyqt6 mpv spectacle scrot playerctl \
               xdotool ydotool wl-clipboard wmctrl

# 2. Clonar e instalar
git clone https://github.com/Fmn1057/claude-voice.git ~/Proyectos/claude-voice
cd ~/Proyectos/claude-voice
python3 -m venv venv
venv/bin/pip install edge-tts webrtcvad sounddevice claude-agent-sdk

# 3. Symlinks
for script in daemon ui speak stt; do
    ln -sf ~/Proyectos/claude-voice/bin/claude-voice-$script ~/.local/bin/claude-voice-$script
done
ln -sf ~/Proyectos/claude-voice/bin/claude-voice ~/.local/bin/claude-voice

# 4. Servicio autostart
cp systemd/claude-voice.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now claude-voice.service
```

### 🪟 Windows 10/11

```powershell
# Clonar e instalar (PowerShell como administrador)
git clone https://github.com/Fmn1057/claude-voice.git claude-voice
cd claude-voice
powershell -ExecutionPolicy Bypass -File windows\install.ps1
```

El instalador crea el venv, instala dependencias, instala mpv y configura el autostart automáticamente. Ver [windows/README.md](windows/README.md) para más detalles.

## Uso

| Acción | Atajo |
|--------|-------|
| Empezar a grabar | `Alt+Z` |
| Dejar de grabar y enviar | `Alt+Z` (segundo press) |
| Interrumpir respuesta de voz | `Alt+Z` (mientras habla) |
| Parar todo inmediatamente | `Alt+X` |

### Ejemplos de comandos de voz

- *"Abre Firefox y busca el clima de Santiago"*
- *"¿Qué caja ves en pantalla?"* — toma screenshot automáticamente
- *"Instala Visual Studio Code"*
- *"Crea una presentación sobre perros y gatos en el escritorio"*
- *"Pon música aleatoria en Spotify"*
- *"Cierra Discord"*

## Estructura del proyecto

```
claude-voice/
├── bin/                          # Scripts Linux
│   ├── claude-voice-daemon       # Daemon principal: hotkeys, grabación, Claude SDK, TTS
│   ├── claude-voice-ui           # Overlay flotante PyQt6 con la conversación
│   ├── claude-voice-speak        # Síntesis de voz (edge-tts + mpv)
│   └── claude-voice-stt          # Transcripción (faster-whisper)
├── windows/                      # Scripts Windows
│   ├── claude-voice-daemon.py    # Daemon adaptado para Windows
│   ├── claude-voice-ui.py        # Overlay PyQt6 (mismo que Linux)
│   ├── install.ps1               # Instalador PowerShell automático
│   ├── launcher.vbs              # Lanzador silencioso para autostart
│   └── README.md                 # Guía específica Windows
├── systemd/
│   └── claude-voice.service      # Servicio systemd (Linux)
├── venv/                         # Entorno virtual Python (no se sube a git)
└── README.md
```

## Cómo funciona

```
Alt+Z ──► graba audio (sounddevice)
           │
           ▼ Alt+Z
        faster-whisper (transcripción local)
           │
           ▼
        Claude Agent SDK (claude-sonnet-4-6)
        ├── tiene acceso a bash, archivos, screenshot
        ├── sesión persistente multi-turno
        └── responde en streaming
           │
           ▼
        edge-tts (oración por oración mientras Claude genera)
        + overlay PyQt6 (muestra texto en tiempo real)
```

## Configuración

Variables de entorno opcionales (en `~/.bashrc` o `~/.zshrc`):

```bash
export CLAUDE_VOICE_MODEL="small"          # Modelo Whisper: tiny, base, small, medium
export CLAUDE_VOICE_LANG="es"             # Idioma de transcripción
export CLAUDE_VOICE_TTS_VOICE="es-MX-DaliaNeural"  # Voz TTS
```

## Logs y diagnóstico

```bash
# Ver log en tiempo real
tail -f /tmp/.claude-voice.log

# Estado del servicio
systemctl --user status claude-voice.service

# Reiniciar
systemctl --user restart claude-voice.service
```

## Notas

- **Juegos en fullscreen (CS2, etc.)**: si el screenshot sale negro, el juego está bloqueando la captura del compositor. Claude igual puede ayudar con comandos de consola del juego.
- **sudo sin contraseña**: para que Claude pueda instalar paquetes, configura `NOPASSWD` en sudoers:
  ```bash
  echo "$(whoami) ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/claude-voice
  sudo chmod 440 /etc/sudoers.d/claude-voice
  ```

## Licencia

MIT
