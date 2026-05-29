# Claude Voice — Instalador para Windows
# Ejecutar como administrador: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$PROJECT = Split-Path -Parent $PSScriptRoot

Write-Host "=== Claude Voice Installer (Windows) ===" -ForegroundColor Cyan

# 1. Verificar Python
Write-Host "`n[1/6] Verificando Python..." -ForegroundColor Yellow
try {
    $pyver = python --version 2>&1
    Write-Host "  OK: $pyver" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python no encontrado. Instalalo desde https://python.org" -ForegroundColor Red
    exit 1
}

# 2. Verificar Claude Code CLI
Write-Host "`n[2/6] Verificando Claude Code CLI..." -ForegroundColor Yellow
try {
    claude --version 2>&1 | Out-Null
    Write-Host "  OK: Claude CLI encontrado" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Claude Code CLI no encontrado." -ForegroundColor Red
    Write-Host "  Descargalo desde: https://claude.ai/download" -ForegroundColor Red
    exit 1
}

# 3. Crear entorno virtual
Write-Host "`n[3/6] Creando entorno virtual Python..." -ForegroundColor Yellow
$venvPath = Join-Path $PROJECT "venv"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
    Write-Host "  OK: venv creado en $venvPath" -ForegroundColor Green
} else {
    Write-Host "  OK: venv ya existe" -ForegroundColor Green
}

# 4. Instalar dependencias Python
Write-Host "`n[4/6] Instalando dependencias Python..." -ForegroundColor Yellow
$pip = Join-Path $venvPath "Scripts\pip.exe"
& $pip install --upgrade pip | Out-Null
& $pip install edge-tts sounddevice faster-whisper keyboard pillow claude-agent-sdk | Out-Null
Write-Host "  OK: dependencias instaladas" -ForegroundColor Green

# 5. Instalar mpv (opcional, via winget o scoop)
Write-Host "`n[5/6] Verificando reproductor de audio (mpv)..." -ForegroundColor Yellow
try {
    mpv --version 2>&1 | Out-Null
    Write-Host "  OK: mpv encontrado" -ForegroundColor Green
} catch {
    Write-Host "  mpv no encontrado, intentando instalar via winget..." -ForegroundColor Yellow
    try {
        winget install mpv.mpv --silent 2>&1 | Out-Null
        Write-Host "  OK: mpv instalado via winget" -ForegroundColor Green
    } catch {
        Write-Host "  AVISO: mpv no pudo instalarse automaticamente." -ForegroundColor Yellow
        Write-Host "  Se usara playsound como fallback. Para mejor calidad: https://mpv.io" -ForegroundColor Yellow
        & $pip install playsound | Out-Null
    }
}

# 6. Crear acceso directo en Inicio (autostart)
Write-Host "`n[6/6] Configurando inicio automatico..." -ForegroundColor Yellow
$startupFolder = [Environment]::GetFolderPath("Startup")
$vbsPath = Join-Path $PSScriptRoot "launcher.vbs"
$shortcutPath = Join-Path $startupFolder "claude-voice.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$vbsPath`""
$Shortcut.WorkingDirectory = $PROJECT
$Shortcut.Description = "Claude Voice Daemon"
$Shortcut.Save()
Write-Host "  OK: acceso directo creado en $startupFolder" -ForegroundColor Green

Write-Host "`n=== Instalacion completa ===" -ForegroundColor Cyan
Write-Host "Iniciando Claude Voice..." -ForegroundColor Green
Start-Process "wscript.exe" -ArgumentList "`"$vbsPath`""
Write-Host "Listo. Usa Alt+Z para hablar, Alt+X para parar." -ForegroundColor Cyan
