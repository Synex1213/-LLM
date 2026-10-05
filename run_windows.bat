@echo off
setlocal
cd /d %~dp0
set NO_PROXY=localhost,127.0.0.1
set no_proxy=localhost,127.0.0.1
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
pause
