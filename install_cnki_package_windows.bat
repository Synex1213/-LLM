@echo off
setlocal
cd /d %~dp0
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
python -c "from integrations.cnki_external import install_package; [print(x.get('message','')) for x in install_package()]"
pause
