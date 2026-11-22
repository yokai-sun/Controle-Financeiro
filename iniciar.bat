@echo off
chcp 65001 >nul
title Minhas Finanças - servidor (feche esta janela para desligar)
cd /d "%~dp0"

rem Se o app já estiver rodando, só abre o navegador
powershell -NoProfile -Command "try{Invoke-WebRequest http://127.0.0.1:5050/api/v1/config -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0}catch{exit 1}" >nul 2>&1
if %errorlevel%==0 (
  start "" http://localhost:5050
  exit /b 0
)

rem Encontra o Python (python ou py)
set "PY="
python -c "import sys" >nul 2>&1 && set "PY=python"
if not defined PY py -c "import sys" >nul 2>&1 && set "PY=py"
if not defined PY (
  echo Python nao encontrado. Rode o install.bat primeiro.
  pause
  exit /b 1
)

%PY% -c "import flask" >nul 2>&1 || (
  echo Instalando dependencias...
  %PY% -m pip install -q -r requirements.txt
)

rem Abre o navegador assim que o servidor responder
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 40;$i++){try{Invoke-WebRequest http://127.0.0.1:5050/api/v1/config -UseBasicParsing -TimeoutSec 1 | Out-Null; Start-Process http://localhost:5050; break}catch{Start-Sleep -Milliseconds 500}}"

%PY% app.py
pause
