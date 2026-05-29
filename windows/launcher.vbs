' Claude Voice — lanzador silencioso (sin ventana de consola)
' Coloca este archivo en la carpeta Inicio de Windows para autostart

Dim projectDir
projectDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
projectDir = Left(projectDir, InStrRev(projectDir, "\") - 1)

Dim pythonExe
pythonExe = projectDir & "\venv\Scripts\pythonw.exe"

Dim daemonScript
daemonScript = projectDir & "\windows\claude-voice-daemon.py"

Dim WshShell
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """" & pythonExe & """ """ & daemonScript & """", 0, False
Set WshShell = Nothing
