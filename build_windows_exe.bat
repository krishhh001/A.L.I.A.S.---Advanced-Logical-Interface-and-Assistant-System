@echo off
setlocal

echo Building ALIAS AI one-file EXE...
where pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo Installing PyInstaller...
  python -m pip install pyinstaller || goto :error
)

pyinstaller --noconfirm --onefile --name ALIASAI --windowed run_friday_qt.py || goto :error

echo.
echo Build complete: dist\ALIASAI.exe
exit /b 0

:error
echo Build failed.
exit /b 1



