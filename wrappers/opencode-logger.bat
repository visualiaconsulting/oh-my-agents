@echo off
REM opencode-logger.bat — Windows shim for the OpenCode logging wrapper
REM Calls the Python wrapper script with all arguments passed through.
python "%~dp0opencode_logger.py" %*
