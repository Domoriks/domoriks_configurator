@echo off
echo Building executable with PyInstaller...

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --icon=domoriks.ico ^
  --add-data "domoriks.ico;." ^
  --name="Domoriks Configurator" ^
  src/main.py

echo Build complete.
pause