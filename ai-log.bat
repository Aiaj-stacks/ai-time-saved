@echo off
REM ai-log.bat - one-click from Windows if you ever run it directly
REM usage: ai-log "task" 2.5 TPM [invested]
python3 "%~dp0log.py" add %*
