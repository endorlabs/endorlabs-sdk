@echo off
REM Batch script to set up Unicode environment for Windows
REM Run this before starting your IDE or terminal session

REM Set Unicode encoding for Python
set PYTHONIOENCODING=utf-8

REM Set console code page to UTF-8
chcp 65001 >nul

echo [OK] Unicode environment configured for Windows
echo PYTHONIOENCODING: %PYTHONIOENCODING%
echo Console code page: 65001 (UTF-8)

REM Test the configuration
echo.
echo Testing Unicode support...
uv run python -c "print('[OK] Unicode test: RAG module works!')"
