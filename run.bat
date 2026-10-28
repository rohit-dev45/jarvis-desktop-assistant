@echo off
REM Usage: run.bat            (text mode)
REM        run.bat --hotkey   (push-to-talk, Ctrl+Alt+J)
REM        run.bat --wake     (say "Hey Jarvis")
cd /d %~dp0
if not exist .venv (
  py -3 -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
if not exist .env (
  copy .env.example .env >nul
  echo Edit .env and add your NVIDIA_API_KEY, then run run.bat again.
  notepad .env
  exit /b
)
python -m jarvis %*
