"""Skill tahminlerini örnek bankasındaki doğrulanmış etiketlerle karşılaştırır.

Kullanım:
    python -I degerlendir.py <tahmin.json> --kaynak <kaynak-id> [--sinif 5]

tahmin.json (skill çıktısının makinece okunur hâli; tmp/ altında tutulur):
    {"kaynak": "<kaynak-id>", "sinif": 5,
     "sorular": [{"ders": "matematik", "no": 1, "cikti": "MAT.5.3.1.", "bilesenler": ["b"], "guven": "yüksek"}, ...]}

Dürüst ölçüm için tahmin, ornek_bul.py --haric <kaynak-id> ile (kitapçığın kendi örnekleri
dışarıda bırakılarak) üretilmiş olmalıdır.

Ölçütler (ders bazında ve toplam):
- Çıktı doğruluğu: öğrenme çıktısı kodu aynı mı.
- Birincil bileşen doğruluğu: çıktı + ilk bileşen aynı mı.
- Yayınevi etiketli sorular ile Claude'un tamamladığı sorular ayrı raporlanır.
- Güven düzeyine göre çıktı doğruluğu (kalibrasyon).
"""
import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortak  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tahmin")
    ap.add_argument("--kaynak")
    ap.add_argument("--sinif", type=int)
    a = ap.parse_args()

    t = ortak.oku(a.tahmin)
    kaynak = a.kaynak or t.get("kaynak")
    sinif = a.sinif or t.get("sinif")
    if not kaynak or not sinif:
        sys.exit("--kaynak ve --sinif gerekli (ya da tahmin.json içinde)")

    tahmin = {(s["ders"], s["no"]): s for s in t["sorular"]}
    dersler = sorted({d for d, _ in tahmin})
    ozet = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # ders -> grup -> [doğru, toplam]
    guven = defaultdict(lambda: [0, 0])
    print(f"{'Ders':<16}{'No':>3}  {'Beklenen':<14}{'Tahmin':<14}{'Güven':<8} Sonuç")
    for ders in dersler:
        beklenen = {x["no"]: x for x in ortak.banka(ders, sinif)["sorular"] if x["kaynak"] == kaynak}
        if not beklenen:
            print(f"{ders:<16} bankada '{kaynak}' kaynağına ait soru yok")
            continue
        for no in sorted(beklenen):
            b = beklenen[no]
            grup = "yayınevi" if b["etiket_kaynagi"] == "yayinevi" else "tamamlanan"
            s = tahmin.get((ders, no))
            if s is None:
                print(f"{ders:<16}{no:>3}  {b['cikti'] + ''.join(b['bilesenler']):<14}{'-- yok --'}")
                ozet[ders][grup + "_cikti"][1] += 1
                ozet[ders][grup + "_bilesen"][1] += 1
                continue
            ok = s["cikti"] == b["cikti"]
            bok = ok and s.get("bilesenler", [])[:1] == b["bilesenler"][:1]
            for anahtar, deger in ((grup + "_cikti", ok), (grup + "_bilesen", bok)):
                ozet[ders][anahtar][0] += deger
                ozet[ders][anahtar][1] += 1
            g = s.get("guven", "?")
            guven[g][0] += ok
            guven[g][1] += 1
            sonuc = ("✓" if ok else "✗ çıktı") + ("" if not ok else (" ✓ bileşen" if bok else " ✗ bileşen"))
            print(f"{ders:<16}{no:>3}  {b['cikti'] + ''.join(b['bilesenler']):<14}"
                  f"{s['cikti'] + ''.join(s.get('bilesenler', [])):<14}{g:<8} {sonuc}"
                  + ("" if grup == "yayınevi" else "  (etiket Claude tamamladı)"))

    def yuzde(d, n):
        return f"{d}/{n} ({100 * d // n}%)" if n else "-"

    print("\nÖZET")
    toplam = defaultdict(lambda: [0, 0])
    for ders, g in ozet.items():
        parcalar = []
        for grup in ("yayınevi", "tamamlanan"):
            c, bl = g[grup + "_cikti"], g[grup + "_bilesen"]
            if c[1]:
                parcalar.append(f"{grup}: çıktı {yuzde(*c)}, çıktı+bileşen {yuzde(*bl)}")
            for k in ("_cikti", "_bilesen"):
                toplam[grup + k][0] += g[grup + k][0]
                toplam[grup + k][1] += g[grup + k][1]
        print(f"  {ders}: " + " | ".join(parcalar))
    for grup in ("yayınevi", "tamamlanan"):
        if toplam[grup + "_cikti"][1]:
            print(f"  TOPLAM {grup}: çıktı {yuzde(*toplam[grup + '_cikti'])}, "
                  f"çıktı+bileşen {yuzde(*toplam[grup + '_bilesen'])}")
    print("Güvene göre çıktı doğruluğu: " + ", ".join(f"{g} {yuzde(*v)}" for g, v in sorted(guven.items())))


if __name__ == "__main__":
    ortak.utf8()
    main()
