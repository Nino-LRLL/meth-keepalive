#!/usr/bin/env bash
# ============================================================
#  Meth - Build script (Linux)
#  Lance les tests puis construit le binaire portable (si PyInstaller
#  est disponible). Meth tourne sur Windows ET Linux (backends natifs
#  sélectionnés par src/backends.py) : ce script produit le binaire
#  Linux, build.bat produit le binaire Windows.
#  Usage: bash build.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/3] Tests unitaires..."
python3 -m unittest discover -s tests -v

echo "[2/3] Compile check..."
python3 -m compileall -q src run.py

echo "[3/3] Build PyInstaller (si disponible)..."
if python3 -c "import PyInstaller" 2>/dev/null; then
    python3 -m PyInstaller --noconfirm Meth.spec
    echo "Portable : dist/Meth/"
else
    echo "PyInstaller absent - build exe ignore (CI Windows le fera)."
fi

echo "=== BUILD TERMINE ==="
