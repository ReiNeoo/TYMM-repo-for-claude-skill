#!/usr/bin/env bash
# Tüm referans verisini kaynaklardan yeniden üretir (5-7. sınıflar).
# Git Bash'te repo kökünden çalıştır:  bash scripts/referans_hepsi.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/Scripts/python.exe -I -W ignore"
PDF=tymm_programmes/pdf_files
ZIP=tymm_programmes/taslak_plans

# 1) PDF metinleri (UTF-8 şart)
mkdir -p tmp/pdf-metin
for f in "$PDF"/*.pdf; do
  ad=$(basename "$f" .pdf | sed 's/_.*//; s/ (.*//')
  pdftotext -enc UTF-8 -layout "$f" "tmp/pdf-metin/$ad.txt"
done

# 2) Taslak planlar
for d in matematik:ortaokul-matematik fen-bilimleri:fen-bilimleri sosyal-bilgiler:sosyal-bilgiler \
         ingilizce:ingilizce ortaokul-turkce:ortaokul-turkce; do
  klasor=${d%%:*}; onek=${d##*:}
  mkdir -p "tmp/plan/$klasor"
  unzip -o -q "$(ls "$ZIP"/"$onek"*.zip)" -d "tmp/plan/$klasor"
done

# 3) Referanslar, plan haftaları, bölme
for s in 5 6 7; do
  for d in matematik fen-bilimleri sosyal-bilgiler ingilizce; do
    $PY scripts/referans_cikar.py "$d" "$s"
  done
  $PY scripts/referans_turkce.py "$s"
  for d in matematik fen-bilimleri sosyal-bilgiler ingilizce turkce; do
    $PY scripts/plan_haftalari.py "$d" "$s" | head -3
    $PY scripts/referans_bol.py "$d" "$s"
  done
done
