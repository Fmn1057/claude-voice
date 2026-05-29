# Claude Voice

Asistente de voz para Linux que controla el escritorio completo usando Claude AI. Activado con **Alt+Z**, transcribe tu voz con Whisper, la envía a Claude con acceso total al sistema, y responde por voz con síntesis de audio neural.

![Demo overlay](https://img.shields.io/badge/KDE_Plasma_6-Wayland-blue) ![Python](https://img.shields.io/badge/Python-3.11+-green) ![Claude](https://img.shields.io/badge/Claude-Sonnet_4-orange)

## Características

- **Alt+Z** — primer press graba, segundo press transcribe y responde
- **Alt+Z** (mientras habla) — interrumpe la voz inmediatamente
- **Alt+X** — para todo (grabación, respuesta, TTS) en el instante
- Overlay flotante en la esquina inferior izquierda con la conversación en streaming
- Transcripción local con **faster-whisper** (sin internet, sin costo)
- Voz neural en español con **edge-tts** (Microsoft Neural, es-MX-DaliaNeural)
- Sesión persistente multi-turno con **Claude Agent SDK**
- Captura de pantalla automática cuando le preguntás sobre lo que ves
- Control total del escritorio: mouse, teclado, ventanas, apps, archivos
- Instala apps, crea documentos, controla Spotify, y más

## Requisitos del sistema

- CachyOS / Arch Linux
- KDE Plasma 6 + Wayland
- Python 3.11+
- Claude Code CLI instalado y autenticado

## Dependencias del sistema

```bash
# Paquetes principales
sudo pacman -S python python-pip python-faster-whisper python-evdev \
               mpv spectacle scrot playerctl

# Para el overlay gráfico
sudo pacman -S python-pyqt6

# Herramientas de escritorio
sudo pacman -S xdotool ydotool wl-clipboard wmctrl
```

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/Fmn1057/claude-voice.git ~/Proyectos/claude-voice
cd ~/Proyectos/claude-voice

# 2. Crear el entorno virtual e instalar dependencias Python
python3 -m venv venv
venv/bin/pip install edge-tts webrtcvad sounddevice claude-agent-sdk

# 3. Crear symlinks en ~/.local/bin
for script in daemon ui speak stt; do
    ln -sf ~/Proyectos/claude-voice/bin/claude-voice-$script ~/.local/bin/claude-voice-$script
done
ln -sf ~/Proyectos/claude-voice/bin/claude-voice ~/.local/bin/claude-voice

# 4. Instalar el servicio systemd
cp systemd/claude-voice.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now claude-voice.service
```

## Uso

| Acción | Atajo |
|--------|-------|
| Empezar a grabar | `Alt+Z` |
| Dejar de grabar y enviar | `Alt+Z` (segundo press) |
| Interrumpir respuesta de voz | `Alt+Z` (mientras habla) |
| Parar todo inmediatamente | `Alt+X` |

### Ejemplos de comandos de voz

- *"Abrí Firefox y buscá el clima de Santiago"*
- *"¿Qué caja ves en pantalla?"* — toma screenshot automáticamente
- *"Instalá Visual Studio Code"*
- *"Creá una presentación sobre perros y gatos en el escritorio"*
- *"Poné música aleatoria en Spotify"*
- *"Cerrá Discord"*

## Estructura del proyecto

```
claude-voice/
├── bin/
│   ├── claude-voice-daemon   # Daemon principal: hotkeys, grabación, Claude SDK, TTS
│   ├── claude-voice-ui       # Overlay flotante PyQt6 con la conversación
│   ├── claude-voice-speak    # Síntesis de voz (edge-tts + mpv)
│   └── claude-voice-stt      # Transcripción (faster-whisper)
├── venv/                     # Entorno virtual Python (no se sube a git)
├── systemd/
│   └── claude-voice.service  # Servicio systemd de usuario
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
- **sudo sin contraseña**: para que Claude pueda instalar paquetes, configurá `NOPASSWD` en sudoers:
  ```bash
  echo "$(whoami) ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/claude-voice
  sudo chmod 440 /etc/sudoers.d/claude-voice
  ```

## Licencia

MIT
