@echo off
REM Preview script for lf file manager (Windows)
REM Uses bat for text files

set "file=%~1"

REM Check if bat exists
where bat >nul 2>&1
if %ERRORLEVEL% equ 0 (
    bat --color=always --style=numbers "%file%" 2>nul || echo %file%
) else (
    type "%file%" 2>nul || echo %file%
)
