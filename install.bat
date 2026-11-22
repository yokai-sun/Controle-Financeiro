@echo off
rem Instalador do Minhas Financas: de dois cliques neste arquivo.
rem Verifica/instala o Python, instala as dependencias e cria o atalho na Area de Trabalho.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\instalar.ps1"
echo.
pause
