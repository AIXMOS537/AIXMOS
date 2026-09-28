@echo off
title AIXMOS STICK
REM Runs everything off this stick. Installs nothing, changes nothing on the PC.
REM   START-HERE.bat          menu
REM   START-HERE.bat jarvis   straight to JARVIS
REM   START-HERE.bat stop     stop what the stick started (do this before unplugging)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0START-HERE.ps1" %*
