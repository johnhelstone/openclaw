@echo off
setlocal enableextensions enabledelayedexpansion

REM ============================================================
REM  WPF Audio Player - Publish script
REM  Bouwt een self-contained single-file .exe voor win-x64
REM  Output: %~dp0publish\WpfAudioPlayer.exe
REM ============================================================

pushd "%~dp0"

echo.
echo ===== WPF Audio Player publish =====
echo Werkmap : %CD%
echo.

where dotnet >nul 2>nul
if errorlevel 1 (
    echo [FOUT] dotnet SDK is niet gevonden in PATH.
    echo Installeer .NET 8 SDK: https://dotnet.microsoft.com/download/dotnet/8.0
    popd
    exit /b 1
)

echo [1/4] dotnet versie:
dotnet --version
echo.

echo [2/4] Oude publish folder opruimen...
if exist "publish" (
    rmdir /s /q "publish"
)
echo.

echo [3/4] Restore + Publish (Release, win-x64, single-file, self-contained)...
dotnet publish "WpfAudioPlayer.csproj" ^
    -c Release ^
    -r win-x64 ^
    --self-contained true ^
    -p:PublishSingleFile=true ^
    -p:IncludeNativeLibrariesForSelfExtract=true ^
    -p:EnableCompressionInSingleFile=true ^
    -p:DebugType=embedded ^
    -o "publish"

if errorlevel 1 (
    echo.
    echo [FOUT] Publish is mislukt.
    popd
    exit /b 1
)

echo.
echo [4/4] Klaar.
echo Output: %CD%\publish\WpfAudioPlayer.exe
echo.

if exist "publish\WpfAudioPlayer.exe" (
    echo Wil je de app nu starten? Druk op een toets, of sluit dit venster om af te breken.
    pause >nul
    start "" "publish\WpfAudioPlayer.exe"
) else (
    echo [WAARSCHUWING] WpfAudioPlayer.exe niet gevonden in publish-folder.
)

popd
endlocal
