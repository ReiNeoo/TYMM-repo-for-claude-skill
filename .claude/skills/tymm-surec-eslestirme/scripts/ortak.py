"""Skill betiklerinin ortak yardımcıları: referans yükleme, metin eşleme, örnek bankası yolları."""
import difflib
import json
import os
import re
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERANS = os.path.join(SKILL, "referans")
ORNEKLER = os.path.join(SKILL, "ornekler")

DERSLER = ("turkce", "matematik", "fen-bilimleri", "sosyal-bilgiler", "ingilizce")
# Yayınevi tablolarında görülen ders adları -> klasör adı. Referansı olmayan dersler None.
DERS_ADI = {
    "TÜRKÇE": "turkce", "MATEMATİK": "matematik", "FEN BİLİMLERİ": "fen-bilimleri",
    "SOSYAL BİLGİLER": "sosyal-bilgiler", "İNGİLİZCE": "ingilizce",
    "FEN": "fen-bilimleri", "SOSYAL": "sosyal-bilgiler",
    "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": None, "DİN K.VE A.B.": None, "DİN": None,
    "T.C. İNKILAP TARİHİ VE ATATÜRKÇÜLÜK": None,
}
# Bazı yayınevleri 5-7. sınıf Sosyal Bilgiler'i "Tarih" diye yazar; 8. sınıfta "Tarih" İnkılap Tarihi'dir.
TARIH_ADLARI = {"TARİH", "TARIH"}


def utf8():
    for akis in (sys.stdout, sys.stderr):
        akis.reconfigure(encoding="utf-8")


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def yaz(yol, veri):
    os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
        f.write("\n")


def ders_klasoru(ad, sinif=None):
    """'MATEMATİK', 'matematik', 'Fen Bilimleri' -> 'matematik' / 'fen-bilimleri'; bilinmiyorsa None.
    'Tarih' yalnızca sınıf 5-7 verilirse Sosyal Bilgiler sayılır."""
    s = ad.strip()
    if s in DERSLER:
        return s
    buyuk = s.replace("i", "İ").replace("ı", "I").upper()
    if buyuk in TARIH_ADLARI:
        return "sosyal-bilgiler" if sinif and sinif < 8 else None
    if buyuk in DERS_ADI:
        return DERS_ADI[buyuk]
    kucuk = s.replace("İ", "i").replace("I", "ı").lower().replace(" ", "-")
    return kucuk if kucuk in DERSLER else None


def ciktilar(ders, sinif):
    """Bir ders/sınıfın tüm öğrenme çıktıları: {kod: {kod, metin, surec_bilesenleri[], tema}}."""
    ref = os.path.join(REFERANS, ders)
    ana = oku(os.path.join(ref, f"{sinif}.json"))
    sonuc = {}
    if "ciktilar" in ana:  # Türkçe: bileşenler beceri alanı dosyalarında
        parcalar = {}
        for c in ana["ciktilar"]:
            yol = os.path.join(ref, c["bilesen_dosyasi"])
            if yol not in parcalar:
                parcalar[yol] = {x["kod"]: x for x in oku(yol)["ciktilar"]}
            sonuc[c["kod"]] = {**parcalar[yol][c["kod"]], "tema": c.get("beceri_alani")}
    else:
        for t in ana["temalar"]:
            liste = t["ciktilar"] if "ciktilar" in t else oku(os.path.join(ref, t["bilesen_dosyasi"]))["ciktilar"]
            for c in liste:
                sonuc[c["kod"]] = {**c, "tema": t.get("ad")}
    return sonuc


def anahtar(m):
    m = m.replace("’", "'").replace("â", "a").replace("î", "i").replace("û", "u")
    m = m.replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"[^a-zçğıöşü]", "", m)


# Yayınevinin programdan biraz farklı yazdığı ama anlamı açıkça aynı olan ifadeler (elle doğrulandı).
# Bunlar benzerlik eşiğinin altında kalan ya da çok kısa oldukları için otomatik yakalanmayan durumlardır.
YAKIN_IFADE = {
    "Güneş’in yapısı ve dönme hareketi ile ilgili bilgileri toplayabilme":
        ("FB.5.1.1.", None, "programda: '… ilgili bilgi toplayabilme'"),
    "Yazım kuralları ve noktalama işaretlerini uygulayabilme":
        ("T.Y.5.16.", None, "programda: 'Yazım ve noktalama işaretleriyle ilgili kuralları uygulayabilme'"),
    "Bilgilendirici metinde anahtar kelimeleri belirlemeye yönelik çözümleme yapabilme":
        ("T.O.5.15.", None, "programda (5. sınıf): 'Metnin anahtar kelimelerini belirlemeye yönelik çözümleme yapabilme'"),
}
YAKIN_IFADE = {anahtar(k): v for k, v in YAKIN_IFADE.items()}
BENZERLIK_ESIGI = 0.9


def metin_esle(metin, cikti_sozlugu):
    """Yayınevi tablosundaki bir kazanım metnini referansla eşler.

    Dönüş: {kod, harf, duzey, [yakin_ifade], [adaylar]}
      duzey: "bilesen" (kod + harf bilinir) | "cikti" (yalnızca kod) | "belirsiz" | "yok"
    Küçük yazım farkları (eksik kelime, ek, noktalama) tolere edilir; tolere edilen eşleşmeye
    'yakin_ifade' notu düşülür.
    """
    a = anahtar(metin)
    if a in YAKIN_IFADE:
        kod, harf, not_ = YAKIN_IFADE[a]
        return {"kod": kod, "harf": harf, "duzey": "bilesen" if harf else "cikti", "yakin_ifade": not_}
    adaylar = []
    for c in cikti_sozlugu.values():
        adaylar.append((anahtar(c["metin"]), c["kod"], None, c["metin"]))
        for b in c["surec_bilesenleri"]:
            adaylar.append((anahtar(b["metin"]), c["kod"], b["harf"], b["metin"]))
    tam = {(x[1], x[2]) for x in adaylar if x[0] == a}
    yakin_not = None
    if not tam:
        puanli = sorted(((difflib.SequenceMatcher(None, a, x[0]).ratio(), x) for x in adaylar),
                        key=lambda p: -p[0])
        if puanli and puanli[0][0] >= BENZERLIK_ESIGI and len(a) > 20:
            en_iyi = puanli[0][0]
            tam = {(x[1], x[2]) for p, x in puanli if p >= en_iyi - 0.02}
            yakin_not = f"programda: '{puanli[0][1][3]}' (benzerlik {en_iyi:.2f})"
    if not tam:
        return {"kod": None, "harf": None, "duzey": "yok"}
    if len(tam) > 1:
        return {"kod": None, "harf": None, "duzey": "belirsiz",
                "adaylar": sorted(f"{k}{h or ''}" for k, h in tam)}
    kod, harf = next(iter(tam))
    sonuc = {"kod": kod, "harf": harf, "duzey": "bilesen" if harf else "cikti"}
    if yakin_not:
        sonuc["yakin_ifade"] = yakin_not
    return sonuc


def banka_yolu(ders, sinif):
    return os.path.join(ORNEKLER, ders, f"{sinif}.json")


def gorsel_klasoru(ders):
    return os.path.join(ORNEKLER, ders, "gorsel")


def banka(ders, sinif):
    yol = banka_yolu(ders, sinif)
    if os.path.exists(yol):
        return oku(yol)
    return {"ders": ders, "sinif": sinif, "kaynaklar": [], "sorular": []}
