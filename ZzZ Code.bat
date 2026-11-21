@echo off
setlocal EnableExtensions
title ZzZ Code
cd /d "%~dp0"

rem Compiled build takes priority; the script is the fallback.
if exist "%~dp0ZzZCode.exe" (
    "%~dp0ZzZCode.exe" %*
    set RC=%ERRORLEVEL%
    goto :done
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 "%~dp0zzzcode_app.py" %*
    set RC=%ERRORLEVEL%
    goto :done
)

python "%~dp0zzzcode_app.py" %*
set RC=%ERRORLEVEL%

:done
if not "%RC%"=="0" pause
exit /b %RC%
