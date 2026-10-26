@echo off
setlocal
cd /d "%~dp0"
title Preparar Proyecto OCR
echo Preparando el entorno local de Proyecto OCR...
where py >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python. Instala Python 3.14 para Windows y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.14 -m venv .venv
  if errorlevel 1 goto :error
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
echo.
echo Preparacion completada. Abre Iniciar OCR.cmd para usar la aplicacion.
exit /b 0
:error
echo.
echo La preparacion no pudo finalizar. Revisa los mensajes anteriores y la conexion a Internet.
pause
exit /b 1
