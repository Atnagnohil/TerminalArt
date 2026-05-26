@echo off
echo ========================================
echo   TerminalArt - PyInstaller
echo ========================================

uv run pyinstaller ^
  --onefile ^
  --console ^
  --name=TerminalArt ^
  --hidden-import=cv2 ^
  --hidden-import=numpy ^
  --hidden-import=PIL ^
  --hidden-import=colorama ^
  src/main.py

if %ERRORLEVEL% EQU 0 (
  echo.
  echo Done: dist\TerminalArt.exe
) else (
  echo.
  echo Build failed
)

pause
