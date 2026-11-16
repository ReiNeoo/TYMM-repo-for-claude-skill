"""Örnek bankasından aday öğrenme çıktılarına ait doğrulanmış soru örneklerini getirir.

Kullanım:
    python -I ornek_bul.py <ders> <sınıf>                       # kapsam özeti + tüm örneklerin tek satırlık listesi
    python -I ornek_bul.py <ders> <sınıf> MAT.5.3.1. MAT.5.3.2. [--bilesen-basina 2] [--haric <kaynak-id> ...]

Kod verilince her çıktı için, her süreç bileşeninden en fazla N örnek listelenir (önce yayınevi etiketliler).
Görsel yolları mutlak yazılır; Read ile açılır. Örneği olmayan bileşenler de gösterilir.
--haric: değerlendirme yaparken test edilen kitapçığın kendi sorularını dışarıda bırakmak için.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortak  # noqa: E402

ONCELIK = {"yayinevi": 0, "yayinevi+claude": 1, "claude": 2}


def satir(x, ders):
    yol = os.path.normpath(os.path.join(ortak.ORNEKLER, ders, x["gorsel"]))
    gorsel = yol if os.path.exists(yol) else "(görsel bu makinede yok)"
    s = f"    [{x['id']}] ({x['etiket_kaynagi']}) {x['ozet']}\n      görsel: {gorsel}"
    if x.get("ipucu"):
        s += f"\n      ipucu: {x['ipucu']}"
    if len(x["bilesenler"]) > 1:
        s += f"\n      bileşenler: {', '.join(x['bilesenler'])}"
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ders")
    ap.add_argument("sinif", type=int)
    ap.add_argument("kodlar", nargs="*")
    ap.add_argument("--bilesen-basina", type=int, default=2)
    ap.add_argument("--haric", nargs="*", default=[])
    a = ap.parse_args()

    ders = ortak.ders_klasoru(a.ders)
    if ders is None:
        sys.exit(f"bilinmeyen ders: {a.ders}")
    b = ortak.banka(ders, a.sinif)
    sorular = [x for x in b["sorular"] if x["kaynak"] not in a.haric]
    ref = ortak.ciktilar(ders, a.sinif)

    if not a.kodlar:
        print(f"{ders} {a.sinif}: {len(sorular)} örnek, {len(b['kaynaklar'])} kaynak"
              + (f" (hariç: {', '.join(a.haric)})" if a.haric else ""))
        say = {}
        for x in sorular:
            for h in x["bilesenler"][:1] or ["-"]:
                say.setdefault(x["cikti"], {}).setdefault(h, 0)
                say[x["cikti"]][h] += 1
        for kod in ref:
            if kod in say:
                print(f"  {kod} " + "  ".join(f"{h}:{n}" for h, n in sorted(say[kod].items())))
        print(f"  örneği olmayan çıktılar: {sum(1 for k in ref if k not in say)}/{len(ref)}")
        print("\nTüm örnekler (id | çıktı+bileşen | özet):")
        for x in sorular:
            print(f"  {x['id']} | {x['cikti']}{''.join(x['bilesenler'])} | {x['ozet']}")
        return

    for kod in a.kodlar:
        kod = kod if kod.endswith(".") else kod + "."
        c = ref.get(kod)
        if c is None:
            print(f"\n{kod}: referansta yok")
            continue
        print(f"\n{kod} {c['metin']}")
        ornekler = sorted((x for x in sorular if x["cikti"] == kod),
                          key=lambda x: (ONCELIK.get(x["etiket_kaynagi"], 9), x["id"]))
        bilesenler = c["surec_bilesenleri"] or [{"harf": None, "metin": "(programda bileşen verilmemiş)"}]
        for bl in bilesenler:
            grup = [x for x in ornekler if (x["bilesenler"][:1] or [None])[0] == bl["harf"]]
            print(f"  {bl['harf'] or '-'}) {bl['metin']}  — {len(grup)} örnek")
            for x in grup[:a.bilesen_basina]:
                print(satir(x, ders))


if __name__ == "__main__":
    ortak.utf8()
    main()
