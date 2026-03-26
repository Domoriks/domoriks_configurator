#!/bin/bash
# Build script for Domoriks Configurator (Linux / macOS)

echo "Building executable with PyInstaller..."

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --icon=domoriks.ico \
  --add-data "domoriks.ico:." \
  --name="Domoriks Configurator" \
  src/main.py

echo "Build complete."
