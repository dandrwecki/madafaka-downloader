@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   Madafaka Downloader - Windows Build
echo   Buduje plik .exe z GUI i wbudowanym ffmpeg
echo ============================================================
echo.

:: Sprawdz czy Python jest dostepny
python --version >nul 2>&1
if errorlevel 1 (
    echo BLAD: Python nie zostal znaleziony.
    echo Pobierz Python z: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: -------------------------------------------------------
echo [1/4] Instalowanie zaleznosci Python...
:: -------------------------------------------------------
pip install yt-dlp mutagen Pillow pyinstaller --quiet --upgrade
if errorlevel 1 (
    echo BLAD: Nie udalo sie zainstalowac zaleznosci.
    pause
    exit /b 1
)
echo OK.

:: -------------------------------------------------------
echo   INFO: Dla pelnej predkosci pobierania wymagany jest Node.js.
echo   Jezeli pobieranie jest wolne (ok. 80 KB/s), zainstaluj Node.js:
echo   https://nodejs.org/  (LTS, Windows Installer)
:: -------------------------------------------------------

:: -------------------------------------------------------
echo [2/4] Pobieranie ffmpeg (statyczna wersja Windows)...
:: -------------------------------------------------------
if exist "ffmpeg.exe" (
    echo ffmpeg.exe juz istnieje - pomijam pobieranie.
) else (
    echo Pobieranie archiwum ffmpeg...
    curl -L -o _ffmpeg_dl.zip "https://github.com/BtbN/ffmpeg-builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    if errorlevel 1 (
        echo BLAD: Nie udalo sie pobrac ffmpeg przez curl.
        echo Pobierz recznie z https://ffmpeg.org i skopiuj ffmpeg.exe i ffprobe.exe tutaj.
        pause
        exit /b 1
    )
    echo Rozpakowywanie...
    python -c "import zipfile,os,shutil; z=zipfile.ZipFile('_ffmpeg_dl.zip'); [shutil.copy2(z.extract(n,'_ffmpeg_tmp'), os.path.basename(n)) for n in z.namelist() if n.endswith('/ffmpeg.exe') or n.endswith('/ffprobe.exe')]; z.close()"
    if errorlevel 1 (
        echo BLAD: Nie udalo sie rozpakowac ffmpeg.
        pause
        exit /b 1
    )
    if exist "_ffmpeg_tmp" rmdir /s /q "_ffmpeg_tmp"
    if exist "_ffmpeg_dl.zip" del /q "_ffmpeg_dl.zip"
    echo ffmpeg gotowy.
)
echo OK.

:: -------------------------------------------------------
echo [3/4] Budowanie pliku exe (PyInstaller)...
:: -------------------------------------------------------
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "madafaka-downloader" ^
    --add-binary "ffmpeg.exe;." ^
    --add-binary "ffprobe.exe;." ^
    youtube_downloader.py

if errorlevel 1 (
    echo BLAD: Budowanie nie powiodlo sie.
    pause
    exit /b 1
)
echo OK.

:: -------------------------------------------------------
echo [4/4] Czyszczenie plikow tymczasowych...
:: -------------------------------------------------------
if exist "build"                    rmdir /s /q "build"
if exist "madafaka-downloader.spec"  del /q "madafaka-downloader.spec"
echo OK.

echo.
echo ============================================================
echo   Gotowe!
echo   Plik: dist\madafaka-downloader.exe
echo   Uruchom dwuklikiem - otworzy sie okno aplikacji.
echo ============================================================

:: Potwierdz ze plik exe istnieje
if exist "dist\madafaka-downloader.exe" (
    echo.
    echo [OK] Plik exe zostal pomyslnie utworzony:
    dir /b "dist\madafaka-downloader.exe"
) else (
    echo.
    echo [UWAGA] Nie znaleziono dist\madafaka-downloader.exe
    echo Sprawdz folder dist\ czy plik nie ma innej nazwy.
    dir /b "dist\" 2>nul
)
pause
