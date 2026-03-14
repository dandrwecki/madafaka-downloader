# madafaka-downloader

Pobiera playlisty i utwory YouTube jako **MP3 · Stereo · 320 kbps**, automatycznie czyści nazwy plików i metadane ID3 pod Rekordbox.

![GUI preview](https://img.shields.io/badge/GUI-tkinter-7c5cbf?style=flat-square) ![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square) ![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey?style=flat-square)

---

## Funkcje

| Krok | Co się dzieje |
|------|---------------|
| 1 | Pobieranie całej playlisty / pojedynczego utworu |
| 2 | Konwersja do MP3 320 kbps stereo 44 100 Hz (ffmpeg) |
| 3 | Czyszczenie nazw plików (usuwanie `[ID]`, znaków specjalnych) |
| 4 | Przepisanie tagów ID3v2.3 (Artist + Title) — gotowe dla Rekordbox |
| 5 | Podsumowanie: pobrane / przetworzone / problematyczne pliki |

---

## Wymagania systemowe

| | macOS | Windows |
|---|---|---|
| Python | 3.9+ (zwykle preinstalowany) | 3.9+ — [python.org](https://www.python.org/downloads/) |
| ffmpeg | przez Homebrew | automatycznie pobierany przez `build_exe.bat` |
| Biblioteki Python | `yt-dlp`, `mutagen` | `yt-dlp`, `mutagen` |

---

## macOS

### Opcja A — uruchom bezpośrednio (Python)

```bash
# 1. Sklonuj lub pobierz repo
git clone https://github.com/TWOJ_NICK/madafaka-downloader.git
cd madafaka-downloader

# 2. Jednorazowy setup (Homebrew + ffmpeg + yt-dlp + mutagen)
bash setup_macos.sh

# 3. Uruchom
python3 youtube_downloader.py
```

Otworzy się okno aplikacji. Wklej URL playlisty i kliknij **Pobierz i oczyść**.

---

### Opcja B — zbuduj .app (dwuklik, bez Pythona)

```bash
bash build_macos.sh
```

Po zakończeniu gotowy bundle znajdziesz w `dist/madafaka-downloader.app`.

**Skopiuj do Aplikacji i uruchamiaj dwuklikiem:**

```bash
cp -r dist/madafaka-downloader.app /Applications/
```

> **Uwaga:** przy pierwszym uruchomieniu macOS może zablokować nieznane źródło.  
> Otwórz **Ustawienia systemowe → Prywatność i bezpieczeństwo** i kliknij „Otwórz mimo to".  
> Alternatywnie: kliknij prawym przyciskiem na `.app` → **Otwórz**.

---

## Windows

### Opcja A — uruchom bezpośrednio (Python)

1. Zainstaluj [Python 3.9+](https://www.python.org/downloads/) — **zaznacz „Add Python to PATH"**
2. Otwórz wiersz poleceń w folderze projektu:

```bat
pip install yt-dlp mutagen
python youtube_downloader.py
```

Pojawi się okno aplikacji. Wklej URL playlisty i kliknij **Pobierz i oczyść**.

---

### Opcja B — zbuduj .exe (dwuklik, bez Pythona)

1. Zainstaluj [Python 3.9+](https://www.python.org/downloads/) — **zaznacz „Add Python to PATH"**
2. Kliknij dwuklikiem **`build_exe.bat`**

Skrypt automatycznie:
- zainstaluje `yt-dlp`, `mutagen`, `pyinstaller`
- pobierze statyczny `ffmpeg.exe` / `ffprobe.exe`
- zbuduje plik wykonywalny

Gotowy `.exe` znajdziesz w `dist\madafaka-downloader.exe` — uruchamiaj **dwuklikiem**.

> **Uwaga:** Windows Defender / SmartScreen może ostrzec o nieznanym wydawcy.  
> Kliknij **„Więcej informacji" → „Uruchom mimo to"**.

---

## Struktura projektu

```
madafaka-downloader/
├── youtube_downloader.py   # główna aplikacja (GUI + logika)
├── requirements.txt        # zależności Python
├── setup_macos.sh          # jednorazowy setup na macOS
├── build_macos.sh          # buduje .app bundle na macOS
└── build_exe.bat           # buduje .exe na Windows
```

---

## Obsługiwane URL-e

- Playlista: `https://www.youtube.com/playlist?list=PLxxxxxxxx`
- Pojedynczy utwór: `https://www.youtube.com/watch?v=xxxxxxxx`
- Skrócony link: `https://youtu.be/xxxxxxxx`

---

## Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---------|-------------|
| `ffmpeg nie znaleziony` | macOS: `brew install ffmpeg` · Windows: uruchom ponownie `build_exe.bat` |
| `yt-dlp nie zainstalowany` | `pip3 install yt-dlp` (macOS) / `pip install yt-dlp` (Windows) |
| Aplikacja zablokowana przez macOS | PPM na `.app` → **Otwórz** lub Ustawienia → Prywatność i bezpieczeństwo |
| SmartScreen na Windows | „Więcej informacji" → „Uruchom mimo to" |
| Plik nie pobiera się | Utwór może być niedostępny w Polsce — spróbuj z VPN |
