"""Yayınevi kazanım tablosunu (xlsx) örnek bankasının standart şablonuna (tablo.json) çevirir.

Kullanım:
    python -I yayinevi_tablo.py <tablo.xlsx> --sinif 5 --kitapcik A --kaynak-id eksen-5-sd1-a \
        --deneme "Eksen 5. Sınıf Süreç Değerlendirme 1" [--yayinevi Eksen] [--tarih 2026-11-10] \
        [--sayfa "Cevap Anahtarı"] -o tmp/ornek/<kaynak-id>/tablo.json

Tanınan sütunlar (başlık satırında, büyük/küçük harf duyarsız):
    Ders | Kazanım* (metin; birden fazla olabilir) | Kazanım Kodu / Kod (varsa) | <kitapçık harfi> (soru no)
Bu biçime uymayan tablolar Claude tarafından elle aynı şablona dönüştürülür (bkz. ORNEK-EKLEME.md).

Her satır için yayınevi metni referansla eşlenir:
    duzey "bilesen" -> çıktı + bileşen tablodan kesin
    duzey "cikti"   -> çıktı tablodan; bileşen Claude tarafından soruya bakılarak tamamlanacak
    duzey "belirsiz"/"yok" -> çıktı ve bileşen Claude tarafından tamamlanacak (serbest etiket, eski program…)
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openpyxl  # noqa: E402

import ortak  # noqa: E402

KOD_DESENI = re.compile(r"^(MAT|FB|SB|ENG|T\.[DOKY])\.\d+\.")


def sutunlar(baslik, kitapcik):
    b = [str(h or "").strip() for h in baslik]
    kucuk = [h.lower() for h in b]
    i_ders = kucuk.index("ders")
    i_kitapcik = b.index(kitapcik)
    metinler = [i for i, h in enumerate(kucuk) if h.startswith("kazanım") and "kod" not in h]
    kodlar = [i for i, h in enumerate(kucuk) if "kod" in h]
    return i_ders, i_kitapcik, metinler, kodlar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--sinif", type=int, required=True)
    ap.add_argument("--kitapcik", required=True)
    ap.add_argument("--kaynak-id", required=True)
    ap.add_argument("--deneme", required=True)
    ap.add_argument("--yayinevi")
    ap.add_argument("--tarih")
    ap.add_argument("--sayfa", help="çalışma sayfası adı (varsayılan: ilk sayfa)")
    ap.add_argument("-o", "--cikis", required=True)
    a = ap.parse_args()

    wb = openpyxl.load_workbook(a.xlsx, data_only=True)
    ws = wb[a.sayfa] if a.sayfa else wb.worksheets[0]
    satirlar_ham = list(ws.iter_rows(values_only=True))
    i_ders, i_no, i_metin, i_kod = sutunlar(satirlar_ham[0], a.kitapcik)

    ref, satirlar = {}, []
    for r in satirlar_ham[1:]:
        if not r[i_ders] or r[i_no] in (None, ""):
            continue
        ders_ad = str(r[i_ders]).strip()
        ders = ortak.ders_klasoru(ders_ad)
        metinler = [str(r[i]).strip() for i in i_metin if r[i]]
        kodlar = [str(r[i]).strip() for i in i_kod if r[i]]
        s = {"ders": ders or ders_ad, "no": int(r[i_no]), "yayinevi_metni": " | ".join(metinler)}
        if kodlar:
            s["yayinevi_kodu"] = " | ".join(kodlar)
        if ders is None:
            s.update(duzey="referans yok", cikti=None, bilesenler=[], etiket_kaynagi=None)
            satirlar.append(s)
            continue
        if ders not in ref:
            ref[ders] = ortak.ciktilar(ders, a.sinif)
        # Önce yayınevi kodu (TYMM biçimindeyse), sonra metinler; en ayrıntılı eşleşme kazanır.
        eslesmeler = []
        for k in kodlar:
            if KOD_DESENI.match(k):
                kod = k if k.endswith(".") else k + "."
                eslesmeler.append({"kod": kod, "harf": None, "duzey": "cikti"} if kod in ref[ders]
                                  else {"kod": None, "harf": None, "duzey": "yok", "not": f"kod referansta yok: {k}"})
        eslesmeler += [ortak.metin_esle(m, ref[ders]) for m in metinler]
        sira = {"bilesen": 0, "cikti": 1, "belirsiz": 2, "yok": 3}
        e = min(eslesmeler, key=lambda x: sira[x["duzey"]]) if eslesmeler else {"duzey": "yok", "kod": None, "harf": None}
        s["duzey"] = e["duzey"]
        s["cikti"] = e["kod"]
        s["bilesenler"] = [e["harf"]] if e.get("harf") else []
        s["etiket_kaynagi"] = "yayinevi" if e["duzey"] == "bilesen" else None  # Claude tamamlayınca dolar
        for k in ("yakin_ifade", "adaylar"):
            if e.get(k):
                s[k] = e[k]
        satirlar.append(s)

    satirlar.sort(key=lambda s: (s["ders"], s["no"]))
    tablo = {
        "kaynak": {"id": a.kaynak_id, "deneme": a.deneme, "yayinevi": a.yayinevi, "sinif": a.sinif,
                   "kitapcik": a.kitapcik, "tarih": a.tarih, "tablo_dosyasi": os.path.basename(a.xlsx)},
        "satirlar": satirlar,
    }
    ortak.yaz(a.cikis, tablo)

    print(f"{'Ders':<18}{'No':>3}  {'Düzey':<13}{'Etiket':<14} Yayınevi metni")
    for s in satirlar:
        et = (s["cikti"] or "-") + "".join(s["bilesenler"])
        print(f"{s['ders'][:17]:<18}{s['no']:>3}  {s['duzey']:<13}{et:<14} {s['yayinevi_metni'][:70]}")
        for k in ("yakin_ifade", "adaylar"):
            if s.get(k):
                print(f"{'':>36}{k}: {s[k]}")
    say = {}
    for s in satirlar:
        say[s["duzey"]] = say.get(s["duzey"], 0) + 1
    print("\nDüzeyler:", ", ".join(f"{k} {v}" for k, v in sorted(say.items())))
    print("Tamamlanacak: duzey 'cikti' -> bileşen; 'belirsiz'/'yok' -> çıktı + bileşen (soruya bakarak).")
    print(f"Yazıldı: {a.cikis}")


if __name__ == "__main__":
    ortak.utf8()
    main()
