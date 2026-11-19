"""Haritadaki her sorunun metnini kendi bölgesinden çıkarır (metin katmanlı PDF; sütun sırası karışmaz).

Kullanım:
    python -I soru_metni.py <kitapçık.pdf> <harita.json> [--onek matematik] [--uzunluk 900]
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf  # noqa: E402

import ortak  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("harita")
    ap.add_argument("--onek", default="")
    ap.add_argument("--uzunluk", type=int, default=0, help="soru başına en fazla karakter (0: tamamı)")
    a = ap.parse_args()
    doc = pymupdf.open(a.pdf)
    for anahtar, bolgeler in ortak.oku(a.harita).items():
        if not anahtar.startswith(a.onek):
            continue
        parca = []
        for b in bolgeler:
            s = doc[b["sayfa"] - 1]
            W, H = s.rect.width, s.rect.height
            x0, y0, x1, y1 = b["kutu"]
            r = pymupdf.Rect(x0 * W, y0 * H, x1 * W, y1 * H)
            satirlar = []
            for blk in s.get_text("dict", clip=r)["blocks"]:
                for ln in blk.get("lines", []):
                    if abs(ln.get("dir", (1, 0))[1]) > 0.05:
                        continue
                    satirlar.append("".join(sp["text"] for sp in ln["spans"]))
            parca.append(" ".join(satirlar))
        metin = re.sub(r"\s+", " ", " ".join(parca)).strip()
        print(f"[{anahtar}] {metin[:a.uzunluk] if a.uzunluk else metin}
")


if __name__ == "__main__":
    ortak.utf8()
    main()
