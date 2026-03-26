#!/bin/bash
# Build script for Domoriks Configurator (Linux / macOS)

echo "Building executable with PyInstaller..."

# Find the PyQt5 plugins directory
QT_PLUGINS=$(python3 -c "from PyQt5.QtCore import QLibraryInfo; print(QLibraryInfo.location(QLibraryInfo.PluginsPath))")

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --icon=domoriks.ico \
  --add-data "domoriks.ico:." \
  --add-binary "${QT_PLUGINS}/platforms/libqxcb.so:PyQt5/Qt5/plugins/platforms/" \
  $([ -f "${QT_PLUGINS}/platforms/libqwayland-generic.so" ] && echo "--add-binary ${QT_PLUGINS}/platforms/libqwayland-generic.so:PyQt5/Qt5/plugins/platforms/") \
  $([ -f "${QT_PLUGINS}/platforms/libqwayland-egl.so" ] && echo "--add-binary ${QT_PLUGINS}/platforms/libqwayland-egl.so:PyQt5/Qt5/plugins/platforms/") \
  $([ -f "${QT_PLUGINS}/platforms/libqwayland-xcomposite-egl.so" ] && echo "--add-binary ${QT_PLUGINS}/platforms/libqwayland-xcomposite-egl.so:PyQt5/Qt5/plugins/platforms/") \
  $([ -f "${QT_PLUGINS}/platforms/libqwayland-xcomposite-glx.so" ] && echo "--add-binary ${QT_PLUGINS}/platforms/libqwayland-xcomposite-glx.so:PyQt5/Qt5/plugins/platforms/") \
  --exclude-module PyQt5.Qt3D \
  --exclude-module PyQt5.QtMultimedia \
  --exclude-module PyQt5.QtWebEngine \
  --exclude-module PyQt5.QtBluetooth \
  --exclude-module PyQt5.QtNfc \
  --exclude-module PyQt5.QtSensors \
  --exclude-module PyQt5.QtSerialPort \
  --exclude-module PyQt5.QtSql \
  --exclude-module PyQt5.QtTest \
  --exclude-module PyQt5.QtTextToSpeech \
  --name="Domoriks Configurator" \
  src/main.py

echo "Build complete."
