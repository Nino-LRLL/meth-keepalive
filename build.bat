@echo off
REM ============================================================
REM  Meth - Build script (Windows)
REM  Construit l'exe portable + l'archive zip + SHA256.
REM  Usage: build.bat
REM ============================================================
setlocal
cd /d "%~dp0"

echo [1/4] Verification de Python...
where python >nul 2>nul
if errorlevel 1 (
    echo ERREUR: Python introuvable sur le PATH.
    exit /b 1
)

echo [2/4] Installation des dependances (requirements + pyinstaller)...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo ERREUR: echec de l'installation des dependances.
    exit /b 1
)

echo [3/4] Build PyInstaller...
python -m PyInstaller --noconfirm Meth.spec
if errorlevel 1 (
    echo ERREUR: le build PyInstaller a echoue.
    exit /b 1
)

echo [4/4] Creation de l'archive portable + SHA256...
if not exist release mkdir release
powershell -NoProfile -Command "Compress-Archive -Path dist\Meth -DestinationPath release\Meth-Portable.zip -Force"
powershell -NoProfile -Command "$h = (Get-FileHash release\Meth-Portable.zip -Algorithm SHA256).Hash; Set-Content -Path release\SHA256.txt -Value ('SHA256 (Meth-Portable.zip): ' + $h)"

echo.
echo === BUILD TERMINE ===
echo Portable : release\Meth-Portable.zip
type release\SHA256.txt
echo.
echo Copiez Meth-Portable.zip n'importe ou, decomprimez, double-cliquez sur Meth.exe.
endlocal
