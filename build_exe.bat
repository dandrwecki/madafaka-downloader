@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   YouTube Playlist Downloader - Windows Build
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
pip install yt-dlp mutagen pyinstaller --quiet --upgrade
if errorlevel 1 (
    echo BLAD: Nie udalo sie zainstalowac zaleznosci.
    pause
    exit /b 1
)
echo OK.

:: -------------------------------------------------------
echo [2/4] Pobieranie ffmpeg (statyczna wersja Windows)...
:: -------------------------------------------------------
if exist "ffmpeg.exe" (
    echo ffmpeg.exe juz istnieje - pomijam pobieranie.
) else (
    powershell -ExecutionPolicy Bypass -Command ^
        "$url = 'https://github.com/BtbN/ffmpeg-builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'; ^
        Write-Host 'Pobieranie archiwum ffmpeg...'; ^
        Invoke-WebRequest -Uri $url -OutFile '_ffmpeg_dl.zip' -UseBasicParsing; ^
        Write-Host 'Rozpakowywanie...'; ^
        Expand-Archive -Path '_ffmpeg_dl.zip' -DestinationPath '_ffmpeg_tmp' -Force; ^
        $binDir = (Get-ChildItem '_ffmpeg_tmp' -Recurse -Filter 'ffmpeg.exe').DirectoryName; ^
        Copy-Item \"$binDir\ffmpeg.exe\" '.' -Force; ^
        Copy-Item \"$binDir\ffprobe.exe\" '.' -Force; ^
        Remove-Item '_ffmpeg_dl.zip' -Force; ^
        Remove-Item '_ffmpeg_tmp' -Recurse -Force; ^
        Write-Host 'ffmpeg gotowy.'"
    if errorlevel 1 (
        echo BLAD: Nie udalo sie pobrac ffmpeg.
        echo Pobierz recznie z https://ffmpeg.org i skopiuj ffmpeg.exe i ffprobe.exe tutaj.
        pause
        exit /b 1
    )
)
echo OK.

:: -------------------------------------------------------
echo [3/4] Budowanie pliku exe (PyInstaller)...
:: -------------------------------------------------------
pyinstaller ^
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
pause
