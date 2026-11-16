"""Tamamlanmış tablo.json'u ve kırpılmış soru görsellerini örnek bankasına ekler.

Kullanım:
    python -I ornek_ekle.py <tablo.json> <soru görselleri klasörü> [--ders matematik ...] [--kuru]

- Görsel adı: <ders>-<no:02d>.png (soru_kirp.py kes çıktısı). Bankaya <kaynak-id>-<no:02d>.png olarak kopyalanır.
- Her satır referansla doğrulanır: çıktı kodu ve bileşen harfleri referansta olmalı.
- Eksik satırlar (çıktı yok, bileşen yok, etiket_kaynagi yok, özet yok) eklenmez; listelenir.
- Aynı kaynak daha önce eklendiyse o kaynağın soruları değiştirilir (betik tekrar çalıştırılabilir).
- --kuru: yalnızca doğrular, bir şey yazmaz.

Banka: ornekler/<ders>/<sınıf>.json (git'te) + ornekler/<ders>/gorsel/*.png (git dışında).
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortak  # noqa: E402

ETIKET_KAYNAKLARI = {"yayinevi", "yayinevi+claude", "claude"}
SORU_ALANLARI = ("ozet", "cikti", "bilesenler", "etiket_kaynagi", "yayinevi_metni", "yayinevi_kodu",
                 "yakin_ifade", "ipucu", "not")


def denetle(s, ref):
    """Satırdaki sorunları döndürür (boş liste = eklenebilir)."""
    sorun = []
    if not s.get("cikti"):
        return ["çıktı kodu yok"]
    c = ref.get(s["cikti"])
    if c is None:
        return [f"çıktı referansta yok: {s['cikti']}"]
    harfler = {b["harf"] for b in c["surec_bilesenleri"]}
    if harfler and not s.get("bilesenler"):
        sorun.append("bileşen yok")
    for h in s.get("bilesenler", []):
        if h not in harfler:
            sorun.append(f"bileşen {h} {s['cikti']} için referansta yok ({','.join(sorted(harfler))})")
    if s.get("etiket_kaynagi") not in ETIKET_KAYNAKLARI:
        sorun.append(f"etiket_kaynagi geçersiz: {s.get('etiket_kaynagi')}")
    if not s.get("ozet"):
        sorun.append("özet yok")
    return sorun


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tablo")
    ap.add_argument("gorseller")
    ap.add_argument("--ders", nargs="*", help="yalnızca bu dersler")
    ap.add_argument("--kuru", action="store_true")
    a = ap.parse_args()

    tablo = ortak.oku(a.tablo)
    kaynak = tablo["kaynak"]
    sinif = kaynak["sinif"]
    dersler = {}
    for s in tablo["satirlar"]:
        if s["ders"] not in ortak.DERSLER:
            continue
        if a.ders and s["ders"] not in a.ders:
            continue
        dersler.setdefault(s["ders"], []).append(s)

    toplam_hata = 0
    for ders, satirlar in dersler.items():
        ref = ortak.ciktilar(ders, sinif)
        b = ortak.banka(ders, sinif)
        yeni, atlanan = [], []
        for s in satirlar:
            sorun = denetle(s, ref)
            gorsel_kaynak = os.path.join(a.gorseller, f"{ders}-{s['no']:02d}.png")
            if not os.path.exists(gorsel_kaynak):
                sorun.append(f"görsel yok: {gorsel_kaynak}")
            if sorun:
                atlanan.append((s["no"], sorun))
                continue
            kimlik = f"{kaynak['id']}-{s['no']:02d}"
            kayit = {"id": kimlik, "kaynak": kaynak["id"], "no": s["no"]}
            kayit.update({k: s[k] for k in SORU_ALANLARI if s.get(k) not in (None, "", [])})
            kayit["gorsel"] = f"gorsel/{kimlik}.png"
            yeni.append((kayit, gorsel_kaynak))

        print(f"\n{ders} {sinif}: {len(yeni)} soru eklenecek, {len(atlanan)} atlandı")
        for no, sorun in atlanan:
            print(f"  {no:>3}: " + "; ".join(sorun))
        toplam_hata += len(atlanan)
        if a.kuru or not yeni:
            continue

        b["sorular"] = [x for x in b["sorular"] if x["kaynak"] != kaynak["id"]] + [k for k, _ in yeni]
        b["sorular"].sort(key=lambda x: (x["kaynak"], x["no"]))
        b["kaynaklar"] = [x for x in b["kaynaklar"] if x["id"] != kaynak["id"]] + [kaynak]
        hedef = ortak.gorsel_klasoru(ders)
        os.makedirs(hedef, exist_ok=True)
        for kayit, kaynak_yol in yeni:
            shutil.copyfile(kaynak_yol, os.path.join(ortak.ORNEKLER, ders, kayit["gorsel"]))
        ortak.yaz(ortak.banka_yolu(ders, sinif), b)
        dagilim = {}
        for x in b["sorular"]:
            dagilim[x["etiket_kaynagi"]] = dagilim.get(x["etiket_kaynagi"], 0) + 1
        print(f"  banka: {len(b['sorular'])} soru, {len(b['kaynaklar'])} kaynak  "
              f"({', '.join(f'{k} {v}' for k, v in sorted(dagilim.items()))})")
    sys.exit(1 if toplam_hata and a.kuru else 0)


if __name__ == "__main__":
    ortak.utf8()
    main()
