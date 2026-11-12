"""Deneme kitapçığı PDF'inin sayfalarını okunabilir PNG'lere çevirir (geliştirme/test için).

Kullanım:
    .venv/Scripts/python.exe -I scripts/sayfa_goruntule.py <kitapçık.pdf> <çıkış klasörü> [--uzun-kenar 2000] [--sutun]

- Her sayfa uzun kenarı en fazla --uzun-kenar piksel olacak şekilde çizilir (taranmış PDF'lerde
  görüntüler çok büyük olabilir).
- --sutun: iki sütunlu sayfalar için ayrıca sol/sağ yarıları üretir (küçük şekil ve harfler
  daha net okunur). Yarılar ortada hafif örtüşür, böylece kenardaki içerik kaybolmaz.
- Her sayfa için metin katmanı olup olmadığını yazdırır.
"""
import argparse
import os
import sys

import pymupdf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("cikis")
    ap.add_argument("--uzun-kenar", type=int, default=2000)
    ap.add_argument("--sutun", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.cikis, exist_ok=True)
    doc = pymupdf.open(a.pdf)
    print(f"{doc.page_count} sayfa")
    for i, sayfa in enumerate(doc, start=1):
        r = sayfa.rect
        olcek = a.uzun_kenar / max(r.width, r.height)
        mat = pymupdf.Matrix(olcek, olcek)
        yol = os.path.join(a.cikis, f"s{i:02d}.png")
        sayfa.get_pixmap(matrix=mat).save(yol)
        metin = len(sayfa.get_text().strip())
        print(f"  s{i:02d}.png  metin katmanı: {'var' if metin else 'yok (taranmış)'}")
        if a.sutun:
            # Yarıları daha yüksek çözünürlükte üret.
            olcek2 = olcek * 1.4
            ortu = r.width * 0.03
            for ad, klip in (("a-sol", pymupdf.Rect(0, 0, r.width / 2 + ortu, r.height)),
                             ("b-sag", pymupdf.Rect(r.width / 2 - ortu, 0, r.width, r.height))):
                sayfa.get_pixmap(matrix=pymupdf.Matrix(olcek2, olcek2), clip=klip).save(
                    os.path.join(a.cikis, f"s{i:02d}-{ad}.png"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
