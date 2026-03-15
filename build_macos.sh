#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  Madafaka Downloader - macOS Build"
echo "  Buduje .app bundle (dwuklik na macOS)"
echo "============================================================"
echo ""

# --- Homebrew ---
if ! command -v brew &>/dev/null; then
    echo "[0/3] Instalowanie Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# --- ffmpeg ---
if ! command -v ffmpeg &>/dev/null; then
    echo "[1/4] Instalowanie ffmpeg..."
    brew install ffmpeg
else
    echo "[1/4] ffmpeg juz zainstalowany."
fi

# --- Node.js (wymagane przez yt-dlp do rozwiazywania n-challenge YouTube) ---
if ! command -v node &>/dev/null; then
    echo "[2/4] Instalowanie Node.js (yt-dlp n-challenge solver)..."
    brew install node
else
    echo "[2/4] Node.js juz zainstalowany."
fi

# --- Python deps ---
echo "[3/4] Instalowanie zaleznosci Python (yt-dlp, mutagen, Pillow, pyinstaller)..."
pip3 install --upgrade yt-dlp mutagen Pillow pyinstaller \
    --break-system-packages 2>/dev/null || \
pip3 install --upgrade yt-dlp mutagen Pillow pyinstaller

# tkinter jest wymagane przez PyInstaller do bundlowania GUI
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
brew install "python-tk@${PY_VER}" 2>/dev/null || true

# --- PyInstaller build ---
echo "[4/4] Budowanie .app bundle (PyInstaller)..."

FFMPEG_BIN=$(which ffmpeg)
FFPROBE_BIN=$(which ffprobe)

# Czyszczenie poprzednich buildow
rm -rf build dist madafaka-downloader.spec

pyinstaller \
    --windowed \
    --name "madafaka-downloader" \
    --add-binary "$FFMPEG_BIN:." \
    --add-binary "$FFPROBE_BIN:." \
    youtube_downloader.py

# Czyszczenie artefaktow
rm -rf build madafaka-downloader.spec

echo ""
echo "============================================================"
echo "  Gotowe!"
echo "  Aplikacja: dist/madafaka-downloader.app"
echo ""
echo "  Aby uruchamiac dwuklikiem, skopiuj do folderu Aplikacje:"
echo "    cp -r dist/madafaka-downloader.app /Applications/"
echo "============================================================"
