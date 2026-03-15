#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  Madafaka Downloader - macOS Setup"
echo "============================================================"
echo ""

# --- Homebrew ---
if ! command -v brew &>/dev/null; then
    echo "[1/4] Instalowanie Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "[1/4] Homebrew juz zainstalowany."
fi

# --- ffmpeg ---
if ! command -v ffmpeg &>/dev/null; then
    echo "[2/4] Instalowanie ffmpeg..."
    brew install ffmpeg
else
    echo "[2/4] ffmpeg juz zainstalowany."
fi

# --- Node.js (wymagane przez yt-dlp do rozwiazywania n-challenge YouTube) ---
if ! command -v node &>/dev/null; then
    echo "[3/4] Instalowanie Node.js (yt-dlp n-challenge solver)..."
    brew install node
else
    echo "[3/4] Node.js juz zainstalowany."
fi

# --- Python deps ---
echo "[4/5] Instalowanie/aktualizowanie zaleznosci Python..."
pip3 install --upgrade yt-dlp mutagen Pillow \
    --break-system-packages 2>/dev/null || \
pip3 install --upgrade yt-dlp mutagen Pillow

# --- tkinter (wymagane dla GUI) ---
echo "[5/5] Instalowanie python-tk (GUI)..."
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
brew install "python-tk@${PY_VER}" 2>/dev/null || true

echo "Gotowe!"
echo ""
echo "============================================================"
echo "  Setup zakończony!"
echo ""
echo "  Uruchamianie bezposrednio:"
echo "    python3 youtube_downloader.py"
echo ""
echo "  Budowanie .app (dwuklik na macOS):"
echo "    bash build_macos.sh"
echo "============================================================"
