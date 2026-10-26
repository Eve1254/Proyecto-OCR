@echo off
setlocal
cd /d "%~dp0"
title Proyecto OCR
if not exist ".venv\Scripts\python.exe" (
  call "Preparar OCR.cmd"
  if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" run.py
if errorlevel 1 (
  echo.
  echo No se pudo iniciar Proyecto OCR. Ejecuta Preparar OCR.cmd y vuelve a intentarlo.
  pause
)
