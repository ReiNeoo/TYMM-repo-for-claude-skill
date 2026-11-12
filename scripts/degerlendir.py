"""Skill tahminlerini altın setle karşılaştırır.

Kullanım:
    .venv/Scripts/python.exe -I scripts/degerlendir.py <tahmin.json> <altın.json> [--kaynak "<ad>"]

tahmin.json biçimi (skill çıktısının makinece okunur hâli; tmp/ altında tutulur):
    {"sorular": [{"no": 1, "cikti": "MAT.5.3.1.", "bilesenler": ["b", "a"], "guven": "yüksek"}, ...]}

Ölçütler:
- Çıktı doğruluğu: tahmin edilen öğrenme çıktısı kodu altın setteki ile aynı mı.
- Bileşen isabeti / kapsamı: yalnızca çıktısı doğru sorularda, bileşen harfleri üzerinden.
- Güven düzeyine göre doğruluk (güven kalibrasyonu).
"""
import argparse
import json
import sys
from collections import defaultdict


def yukle(yol):
    return json.load(open(yol, encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tahmin")
    ap.add_argument("altin")
    ap.add_argument("--kaynak", help="altın setteki kaynak adı (birden fazla kaynak varsa)")
    ap.add_argument("--ders", help="çok dersli tahmin dosyasında yalnızca bu dersin soruları "
                                   "(sorulardaki 'ders' alanı, ör. turkce)")
    a = ap.parse_args()

    altin = yukle(a.altin)
    kaynaklar = altin["kaynaklar"]
    if a.kaynak:
        kaynaklar = [k for k in kaynaklar if k["ad"] == a.kaynak]
    beklenen = {s["no"]: s for k in kaynaklar for s in k["sorular"]}
    tahmin = {s["no"]: s for s in yukle(a.tahmin)["sorular"]
              if not a.ders or s.get("ders") == a.ders}

    dogru = 0
    birincil = 0  # tahmindeki ilk bileşen, beklenen ilk bileşenle aynı ve çıktı doğru
    tp = fp = fn = 0
    guven = defaultdict(lambda: [0, 0])
    print(f"{'No':>3}  {'Beklenen':<14} {'Tahmin':<14} Bileşen (beklenen / tahmin)")
    for no in sorted(beklenen):
        b = beklenen[no]
        t = tahmin.get(no)
        if t is None:
            print(f"{no:>3}  {b['cikti']:<14} {'-- yok --':<14}")
            continue
        ok = t["cikti"] == b["cikti"]
        dogru += ok
        g = t.get("guven", "?")
        guven[g][0] += ok
        guven[g][1] += 1
        bb, tb = set(b["bilesenler"]), set(t.get("bilesenler", []))
        if ok and t.get("bilesenler") and t["bilesenler"][0] == b["bilesenler"][0]:
            birincil += 1
        if ok:
            tp += len(bb & tb)
            fp += len(tb - bb)
            fn += len(bb - tb)
        isaret = "✓" if ok else "✗"
        print(f"{no:>3}  {b['cikti']:<14} {t['cikti']:<14} {isaret} "
              f"{','.join(b['bilesenler'])} / {','.join(t.get('bilesenler', []))}")

    n = len(beklenen)
    print(f"\nÇıktı doğruluğu: {dogru}/{n} ({100 * dogru / n:.0f}%)" if n else "Altın set boş.")
    if n:
        print(f"Birincil bileşen doğruluğu (çıktı + ilk bileşen): {birincil}/{n} ({100 * birincil / n:.0f}%)")
    if tp + fp:
        print(f"Bileşen isabeti (precision): {tp}/{tp + fp} ({100 * tp / (tp + fp):.0f}%)")
    if tp + fn:
        print(f"Bileşen kapsamı (recall):    {tp}/{tp + fn} ({100 * tp / (tp + fn):.0f}%)")
    print("Güvene göre çıktı doğruluğu:")
    for g, (d, t) in sorted(guven.items()):
        print(f"  {g}: {d}/{t}")
    fazla = sorted(set(tahmin) - set(beklenen))
    if fazla:
        print(f"Altın sette olmayan tahminler: {fazla}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
