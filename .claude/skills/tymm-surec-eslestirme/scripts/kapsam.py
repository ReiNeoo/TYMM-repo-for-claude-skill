"""Bir ders/sınıfın öğrenme çıktılarını ve süreç bileşenlerini kısa biçimde listeler (aday seçimi için).

Kullanım:
    python -I kapsam.py <ders> <sınıf> [--hafta N] [--kodlar KOD ...]
--hafta N: yalnızca plan haftası N'e kadar başlayan çıktılar (plan haftası olmayanlar da yazılır).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortak  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ders")
    ap.add_argument("sinif", type=int)
    ap.add_argument("--hafta", type=int)
    ap.add_argument("--kodlar", nargs="*")
    a = ap.parse_args()
    ders = ortak.ders_klasoru(a.ders, a.sinif)
    for kod, c in ortak.ciktilar(ders, a.sinif).items():
        hf = c.get("plan_haftalari") or []
        if a.kodlar and kod not in [k if k.endswith(".") else k + "." for k in a.kodlar]:
            continue
        if a.hafta and hf and min(hf) > a.hafta:
            continue
        print(f"{kod} [{c.get('tema', '')}] (hafta {','.join(map(str, hf)) or '-'}) {c['metin']}")
        for b in c["surec_bilesenleri"]:
            print(f"   {b['harf']}) {b['metin']}")


if __name__ == "__main__":
    ortak.utf8()
    main()
