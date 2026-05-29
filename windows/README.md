# Claude Voice — Windows

Misma experiencia que la versión Linux: **Alt+Z** para hablar, Claude controla tu PC y responde por voz.

## Requisitos

- Windows 10/11 (64-bit)
- Python 3.11 o superior → [python.org](https://python.org)
- Claude Code CLI → [claude.ai/download](https://claude.ai/download)
- Micrófono

## Instalación rápida

Abre PowerShell **como administrador** y ejecuta:

```powershell
cd C:\ruta\donde\clonaste\claude-voice
powershell -ExecutionPolicy Bypass -File windows\install.ps1
```

El instalador hace todo automáticamente:
1. Crea el entorno virtual Python (`venv/`)
2. Instala todas las dependencias
3. Instala `mpv` para reproducción de audio (via winget)
4. Crea un acceso directo en la carpeta Inicio de Windows (autostart)
5. Lanza el daemon

## Instalación manual

```powershell
# 1. Crear venv
python -m venv venv
venv\Scripts\pip install edge-tts sounddevice faster-whisper keyboard pillow claude-agent-sdk

# 2. Instalar mpv (recomendado)
winget install mpv.mpv
# O desde: https://mpv.io/installation/

# 3. Ejecutar
venv\Scripts\pythonw.exe windows\claude-voice-daemon.py
```

## Uso

| Acción | Atajo |
|--------|-------|
| Empezar a grabar | `Alt+Z` |
| Dejar de grabar y enviar | `Alt+Z` (segundo press) |
| Interrumpir voz | `Alt+Z` (mientras habla) |
| Parar todo | `Alt+X` |

## Autostart

El instalador ya lo configura. Si querés hacerlo manualmente:

1. Presiona `Win+R` → escribe `shell:startup` → Enter
2. Copia `launcher.vbs` ahí (o crea un acceso directo)

## Diferencias con la versión Linux

| Función | Linux | Windows |
|---------|-------|---------|
| Hotkeys | evdev (kernel) | `keyboard` library |
| Screenshot | spectacle / scrot | PIL ImageGrab |
| Matar procesos | pkill | taskkill |
| Audio | mpv | mpv / playsound |
| Autostart | systemd | Carpeta Inicio |
| Control escritorio | xdotool / ydotool | PowerShell / SendKeys |

## Logs

Los logs se guardan en `%TEMP%\claude-voice.log`:

```powershell
Get-Content $env:TEMP\claude-voice.log -Wait
```

## Problemas comunes

**"No module named keyboard"** → `venv\Scripts\pip install keyboard`

**El hotkey no funciona en algunos juegos** → Ejecutar el daemon como administrador

**Sin audio** → Instalar mpv: `winget install mpv.mpv`

**"Access denied" en hotkeys** → Ejecutar PowerShell como administrador
