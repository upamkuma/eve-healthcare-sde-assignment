@echo off
python -m pip install -r requirements.txt
python -m pytest -q
pause
