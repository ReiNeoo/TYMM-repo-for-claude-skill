"""Yayınevi cevap anahtarındaki kazanım metinlerini referanstaki kodlara eşler ve tahminle karşılaştırır.

Yayınevi tablolarında çoğunlukla kod yoktur; yalnızca öğrenme çıktısı ya da süreç bileşeni
metni vardır. Bu betik her metni referans dosyasındaki metinlerle (önce birebir, sonra baş/son
farkına toleranslı) eşler:
  - öğrenme çıktısı metniyle eşleşirse  -> düzey "cikti"   (yalnızca kod bilinir)
  - süreç bileşeni metniyle eşleşirse   -> düzey "bilesen" (kod + harf bilinir)
  - hiçbiriyle eşleşmezse               -> düzey "yok" (TYMM dışı / eski program / serbest etiket)

Kullanım:
    .venv/Scripts/python.exe -I scripts/yayinevi_esle.py <cevap.xlsx> <sınıf> <kitapçık> <tahmin.json>...
Çıktı: ders bazında doğruluk tablosu; eşleşmeler <cevap.xlsx yanına> yayinevi_eslesme.json
"""
import json
import os
import re
import sys

import openpyxl

DERS = {"TÜRKÇE": "turkce", "MATEMATİK": "matematik", "FEN BİLİMLERİ": "fen-bilimleri",
        "SOSYAL BİLGİLER": "sosyal-bilgiler", "İNGİLİZCE": "ingilizce"}
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def anahtar(m):
    m = m.replace("’", "'").replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"[^a-zçğıöşüâîû]", "", m)


def referans_metinleri(ders, sinif):
    """[(anahtar, kod, harf|None, metin)] — çıktılar ve bileşenler."""
    ref = os.path.join(KOK, "skill", "tymm-surec-eslestirme", "referans", ders)
    ana = json.load(open(os.path.join(ref, f"{sinif}.json"), encoding="utf-8"))
    ciktilar = []
    if "ciktilar" in ana:  # Türkçe
        parcalar = {}
        for c in ana["ciktilar"]:
            yol = os.path.join(ref, c["bilesen_dosyasi"])
            parcalar.setdefault(yol, {x["kod"]: x for x in json.load(open(yol, encoding="utf-8"))["ciktilar"]})
            ciktilar.append(parcalar[yol][c["kod"]])
    else:
        for t in ana["temalar"]:
            if "ciktilar" in t:
                ciktilar += t["ciktilar"]
            else:  # İngilizce
                ciktilar += json.load(open(os.path.join(ref, t["bilesen_dosyasi"]), encoding="utf-8"))["ciktilar"]
    sonuc = []
    for c in ciktilar:
        sonuc.append((anahtar(c["metin"]), c["kod"], None, c["metin"]))
        for b in c["surec_bilesenleri"]:
            sonuc.append((anahtar(b["metin"]), c["kod"], b["harf"], b["metin"]))
    return sonuc


# Yayınevinin programdan biraz farklı yazdığı ama anlamı açıkça aynı olan ifadeler (elle doğrulandı).
# Program ifadesine benzemeyen serbest etiketler ("Eş Anlamlı Kelimeler" vb.) buraya EKLENMEZ.
YAKIN_IFADE = {
    "Ay’ın özellikleri, dönme ve dolanma hareketleri ile ilgili verileri değerlendirir.":
        ("FB.5.1.2.", "c", "programda: '… verileri yorumlar ve değerlendirir.'"),
    "Güneş’in yapısı ve dönme hareketi ile ilgili bilgileri toplayabilme":
        ("FB.5.1.1.", None, "programda: '… ilgili bilgi toplayabilme'"),
    "Yazım kuralları ve noktalama işaretlerini uygulayabilme":
        ("T.Y.5.16.", None, "programda: 'Yazım ve noktalama işaretleriyle ilgili kuralları uygulayabilme'"),
    "Bilgilendirici metinde anahtar kelimeleri belirlemeye yönelik çözümleme yapabilme":
        ("T.O.5.15.", None, "programda (5. sınıf): 'Metnin anahtar kelimelerini belirlemeye yönelik çözümleme yapabilme'"),
}
YAKIN_IFADE = {anahtar(k): v for k, v in YAKIN_IFADE.items()}


def esle(metin, adaylar):
    a = anahtar(metin)
    if a in YAKIN_IFADE:
        kod, harf, not_ = YAKIN_IFADE[a]
        return {"kod": kod, "harf": harf, "duzey": "bilesen" if harf else "cikti", "yakin_ifade": not_}
    tam = [x for x in adaylar if x[0] == a]
    if not tam:  # baş/son farkı (ör. "toplayabilme" / "bilgi toplayabilme", sondaki nokta)
        tam = [x for x in adaylar if len(a) > 25 and (x[0].startswith(a) or a.startswith(x[0])
               or x[0].endswith(a) or a.endswith(x[0])) and abs(len(x[0]) - len(a)) <= 15]
    kodlar = {(x[1], x[2]) for x in tam}
    if len({k for k, _ in kodlar}) == 1 and len(kodlar) == 1:
        kod, harf = next(iter(kodlar))
        return {"kod": kod, "harf": harf, "duzey": "bilesen" if harf else "cikti"}
    if len({k for k, _ in kodlar}) > 1:
        return {"kod": None, "harf": None, "duzey": "belirsiz", "adaylar": sorted({k for k, _ in kodlar})}
    return {"kod": None, "harf": None, "duzey": "yok"}


def main():
    xlsx, sinif, kitapcik, *tahmin_dosyalari = sys.argv[1:]
    sinif = int(sinif)
    ws = openpyxl.load_workbook(xlsx, data_only=True).worksheets[0]
    basliklar = [str(h).strip() for h in next(ws.iter_rows(values_only=True))]
    i_ders, i_metin, i_no = basliklar.index("Ders"), basliklar.index("Kazanım-1"), basliklar.index(kitapcik)

    tahmin = {}
    for f in tahmin_dosyalari:
        for s in json.load(open(f, encoding="utf-8"))["sorular"]:
            tahmin[(s["ders"], s["no"])] = s

    ref_cache, satirlar = {}, []
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if not r[i_ders]:
            continue
        ders = DERS.get(str(r[i_ders]).strip())
        no, metin = int(r[i_no]), str(r[i_metin]).strip()
        if ders is None:
            satirlar.append({"ders": str(r[i_ders]).strip(), "no": no, "metin": metin, "duzey": "referans yok"})
            continue
        if ders not in ref_cache:
            ref_cache[ders] = referans_metinleri(ders, sinif)
        satirlar.append({"ders": ders, "no": no, "metin": metin, **esle(metin, ref_cache[ders])})

    print(f"{'Ders':<16}{'No':>3}  {'Yayınevi':<14}{'Düzey':<9} {'Tahmin':<14} Sonuç")
    ozet = {}
    for s in sorted(satirlar, key=lambda s: (s["ders"], s["no"])):
        t = tahmin.get((s["ders"], s["no"]))
        o = ozet.setdefault(s["ders"], {"n": 0, "kodlu": 0, "cikti": 0, "bil_n": 0, "bil": 0, "yok": 0})
        o["n"] += 1
        sonuc = ""
        if s["duzey"] in ("cikti", "bilesen") and t:
            o["kodlu"] += 1
            ok = t["cikti"] == s["kod"]
            o["cikti"] += ok
            sonuc = "✓" if ok else "✗"
            if s["duzey"] == "bilesen":
                o["bil_n"] += 1
                bok = ok and t["bilesenler"][:1] == [s["harf"]]
                o["bil"] += bok
                sonuc += " bileşen " + ("✓" if bok else f"✗ ({','.join(t['bilesenler']) or '-'})")
        else:
            o["yok"] += 1
            sonuc = s["duzey"] + (f" {s.get('adaylar')}" if s.get("adaylar") else "")
        yk = (s.get("kod") or "-") + (s.get("harf") or "")
        print(f"{s['ders']:<16}{s['no']:>3}  {yk:<14}{s['duzey']:<9} "
              f"{(t['cikti'] + ''.join(t['bilesenler'][:1])) if t else '-':<14} {sonuc}")
        if s["duzey"] in ("yok", "belirsiz"):
            print(f"{'':>21}yayınevi metni: {s['metin']}")

    print("\nÖZET")
    for d, o in ozet.items():
        if o["kodlu"] == 0:
            print(f"  {d}: {o['n']} soru, hiçbiri TYMM referansıyla eşlenemedi")
            continue
        bil = f", birincil bileşen {o['bil']}/{o['bil_n']}" if o["bil_n"] else ""
        print(f"  {d}: öğrenme çıktısı {o['cikti']}/{o['kodlu']} ({100 * o['cikti'] // o['kodlu']}%){bil}"
              f"; eşlenemeyen {o['yok']}")
    cikis = os.path.join(os.path.dirname(xlsx), "yayinevi_eslesme.json")
    json.dump(satirlar, open(cikis, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
