"""Türkçe program PDF'inden referans JSON'u üretir.

Türkçe programında süreç bileşenleri tema sayfalarında değil, "9. Tablo: Öğrenme Çıktıları, Süreç
Bileşenleri ve Açıklamalar" içinde verilir; aynı satırda 5-8. sınıf kodları yan yana durur.
Bu yüzden iki kaynak birleştirilir:
  1. Tema sayfaları (pdftotext metni): tema adı, ders saati, kod -> öğrenme çıktısı başlığı
  2. 9. Tablo (PyMuPDF, yalnızca sol sütun blokları): başlık -> süreç bileşenleri
Eşleştirme başlık metni üzerinden yapılır.

Kullanım:
    pdftotext -enc UTF-8 -layout "<türkçe.pdf>" tmp/pdf-metin/ortaokul-turkce-dersi.txt
    .venv/Scripts/python.exe -I scripts/referans_turkce.py <sınıf>
"""
import json
import os
import re
import sys

import pymupdf

PDF = "ortaokul-turkce-dersi_20260902_111157_977.pdf"
TXT = "ortaokul-turkce-dersi.txt"
TR_ALFABE = "abcçdefgğhıijklmnoöprsştuüvyz"
BECERILER = {"D": "Dinleme/İzleme", "O": "Okuma", "K": "Konuşma", "Y": "Yazma"}

KOD_RE = re.compile(r"T\.([DOKY])\.(\d)\.(\d+)\.")
BILESEN_RE = re.compile(r"^([a-zçğıöşü])\)\s*(.*)$", re.S)
TEMA_RE = re.compile(r"^\s*(\d+)\.\s*TEMA\s*:\s*(.+?)\s*$")
# 9. Tablo'da öğrenme çıktısı olmayan satırlar: "Sözlü Üretim ✔ / Sözlü Etkileşim ✔" kutucukları
# ve bunları açıklayan not.
ATLA_RE = re.compile(r"✔|(Sözlü|Yazılı) Üretim|(Sözlü|Yazılı) Etkileşim|süreçlerinin hangisine|"
                     r"kutucuklara onay")


def birlestir(parcalar):
    sonuc = ""
    for p in parcalar:
        p = p.replace("\xad", "").strip()
        if not p:
            continue
        if sonuc.endswith("-") and not sonuc.endswith(" -"):
            sonuc = sonuc[:-1] + p
        elif sonuc:
            sonuc += " " + p
        else:
            sonuc = p
    return re.sub(r"\s+", " ", sonuc).strip()


def anahtar(metin):
    return re.sub(r"[^a-zçğıöşüâîû]", "", metin.lower())


# ---------------------------------------------------------------- 9. Tablo
def tablo9(pdf_yolu):
    """[{baslik, bilesenler:[{harf, metin}], kodlar:set, sayfa}] döndürür."""
    doc = pymupdf.open(pdf_yolu)
    sayfalar = [i for i in range(doc.page_count) if "ALAN BECERİSİ:" in doc[i].get_text()]
    # Sayfalar yan çevrilmiş; sol sütundaki (öğrenme çıktısı + bileşenler) her satır aynı kenarda
    # (y1 ≈ 795.6) biter. Blok değil satır düzeyinde süzülür, çünkü bazı bloklar sol sütunla
    # açıklama sütununu birleştirir.
    alanlar = {"DİNLEME/İZLEME": "D", "OKUMA": "O", "KONUŞMA": "K", "YAZMA": "Y"}
    satirlar = []
    for i in sayfalar:
        m = re.search(r"ALAN BECERİSİ:\s*(DİNLEME/İZLEME|OKUMA|KONUŞMA|YAZMA)", doc[i].get_text())
        beceri = alanlar[m.group(1)] if m else None
        sayfa_satirlari = []
        for blok in doc[i].get_text("dict")["blocks"]:
            for satir in blok.get("lines", []):
                x0, _, _, y1 = satir["bbox"]
                metin = "".join(sp["text"] for sp in satir["spans"]).strip()
                if abs(y1 - 795.6) < 2 and metin and "Tablo" not in metin \
                        and not ATLA_RE.search(metin):
                    sayfa_satirlari.append((x0, metin))
        for x0, metin in sorted(sayfa_satirlari):
            kodlar = set(KOD_RE.findall(metin))
            metin = KOD_RE.sub("", metin).strip()
            if metin or kodlar:
                satirlar.append((i + 1, beceri, metin, kodlar))

    satir_listesi, mevcut, hedef = [], None, None
    for sayfa, beceri, metin, kodlar in satirlar:
        if mevcut is not None:
            mevcut["kodlar"] |= {f"T.{a}.{b}.{c}." for a, b, c in kodlar}
        if not metin:
            continue
        m = BILESEN_RE.match(metin)
        if m and mevcut is not None and mevcut["_baslik_tamam"]:
            b = {"harf": m.group(1), "_parca": [m.group(2)]}
            mevcut["bilesenler"].append(b)
            hedef = b["_parca"]
            continue
        # Bileşen değilse: ya önceki metnin devamı ya da yeni bir başlık.
        if mevcut is not None and not mevcut["_baslik_tamam"]:
            mevcut["_baslik"].append(metin)
            mevcut["_baslik_tamam"] = birlestir(mevcut["_baslik"]).endswith("me")
            continue
        if hedef is not None and not birlestir(hedef).endswith("."):
            hedef.append(metin)
            continue
        mevcut = {"_baslik": [metin], "bilesenler": [], "kodlar": set(), "sayfa": sayfa,
                  "beceri": beceri}
        mevcut["_baslik_tamam"] = birlestir([metin]).endswith("me")
        satir_listesi.append(mevcut)
        hedef = None

    for s in satir_listesi:
        s["baslik"] = birlestir(s.pop("_baslik"))
        s.pop("_baslik_tamam")
        for b in s["bilesenler"]:
            b["metin"] = birlestir(b.pop("_parca"))
    return satir_listesi


# ---------------------------------------------------------------- Tema sayfaları
def tema_sayfalari(txt_yolu, sinif):
    metin = open(txt_yolu, encoding="utf-8").read()
    temalar, tema, blokta, son = [], None, False, None
    for sayfa_no, sayfa in enumerate(metin.split("\f"), start=1):
        for s in sayfa.split("\n"):
            s = s.rstrip()
            m = TEMA_RE.match(s)
            if m and not blokta:
                tema = {"pdf_sira": int(m.group(1)), "ad": m.group(2), "ders_saati": None,
                        "sayfa": sayfa_no, "kodlar": []}
                temalar.append(tema)
                continue
            if tema is None:
                continue
            if tema["ders_saati"] is None:
                m = re.search(r"DERS SAATİ\s+(\d+)", s)
                if m:
                    tema["ders_saati"] = int(m.group(1))
            if not blokta:
                if s.strip().startswith("ÖĞRENME ÇIKTILARI"):
                    blokta, son = True, None
                continue
            if "İÇERİK ÇERÇEVESİ" in s:
                blokta, son = False, None
                continue
            temiz = s.strip()
            if not temiz or temiz.isdigit() or "DERSİ ÖĞRETİM PROGRAMI" in temiz:
                continue
            m = re.search(rf"T\.([DOKY])\.{sinif}\.(\d+)\.\s*(.*)$", temiz)
            if m:
                son = {"kod": f"T.{m.group(1)}.{sinif}.{m.group(2)}.", "_parca": [m.group(3)],
                       "sayfa": sayfa_no}
                tema["kodlar"].append(son)
                continue
            if temiz in ("Dinleme/İzleme", "Okuma", "Konuşma", "Yazma"):
                son = None
                continue
            if son is not None and not birlestir(son["_parca"]).endswith("me"):
                son["_parca"].append(temiz)
    sonuc = []
    for t in temalar:
        if not t["kodlar"]:
            continue
        for k in t["kodlar"]:
            k["baslik"] = birlestir(k.pop("_parca"))
        sonuc.append(t)
    return sonuc


def tema_tablosu(txt_yolu, sinif):
    """'<sinif>. Sınıf Tema Öğrenme Çıktıları Sayısı ve Süre Tablosu' -> [(tema no, çıktı sayısı)]."""
    satirlar = open(txt_yolu, encoding="utf-8").read().split("\n")
    sonuc, icinde = {}, False
    for s in satirlar:
        if re.search(rf"Tablo:\s*{sinif}\. Sınıf Tema Öğrenme Çıktıları Sayısı", s):
            icinde = True
            continue
        if icinde:
            m = re.match(r"^\s*(\d)\.\s*TEMA\s+.+?\s{2,}(\d+)\s+(\d+)\s+(\d+)", s)
            if m:
                sonuc[int(m.group(1))] = int(m.group(2))
            if len(sonuc) == 6:
                break
    return sonuc


def main():
    sinif = int(sys.argv[1])
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    txt = os.path.join(kok, "tmp", "pdf-metin", TXT)
    satirlar = tablo9(os.path.join(kok, "tymm_programmes", "pdf_files", PDF))
    temalar = tema_sayfalari(txt, sinif)
    beklenen = tema_tablosu(txt, sinif)

    # Başlık -> 9. Tablo satırı. Aynı başlık birden fazla satırda olabilir (ör. farklı beceri
    # alanlarında); o zaman satırdaki kodlarla ayırt edilir.
    indeks = {}
    for s in satirlar:
        indeks.setdefault(anahtar(s["baslik"]), []).append(s)

    uyarilar, notlar, bilgiler = [], set(), set()

    def daralt(kod, adaylar):
        """Aynı başlık farklı beceri alanlarında olabilir (ör. Dinleme ve Okuma'da
        'Bilgilendirici metinde …'). Önce sayfanın ALAN BECERİSİ başlığına, sonra koda göre ayır."""
        beceri = kod.split(".")[1]
        ayni = [s for s in adaylar if s["beceri"] == beceri]
        adaylar = ayni or adaylar
        if len(adaylar) > 1:
            kodlu = [s for s in adaylar if kod in s["kodlar"]]
            adaylar = kodlu or adaylar
        return adaylar

    def satir_bul(kod, baslik):
        adaylar = daralt(kod, indeks.get(anahtar(baslik), []))
        if len(adaylar) == 1:
            return adaylar[0]
        if len(adaylar) > 1:
            uyarilar.append(f"{kod} birden fazla 9. Tablo satırıyla eşleşti: '{baslik}'")
            return None
        # Yalnızca zararsız farka izin ver: biri diğerinin başı ve fark kısa (ör. tema sayfasında
        # "… çözümleme" / tabloda "… çözümleme yapabilme"). "Okumada …" ~ "Yazmada …" gibi
        # benzer ama farklı başlıklar asla eşleştirilmez.
        a = anahtar(baslik)
        yakin = [k for k in indeks if (k.startswith(a) or a.startswith(k)) and abs(len(k) - len(a)) <= 12]
        if len(yakin) == 1:
            adaylar = daralt(kod, indeks[yakin[0]])
            if len(adaylar) == 1:
                bilgiler.add(f"{kod} başlık sonu farkıyla eşleşti: '{baslik}' ~ '{adaylar[0]['baslik']}'")
                return adaylar[0]
        return None

    cikti_temalar = []
    for t in temalar:
        ciktilar = []
        for k in t["kodlar"]:
            s = satir_bul(k["kod"], k["baslik"])
            if s is None:
                uyarilar.append(f"{k['kod']} 9. Tablo'da bulunamadı: '{k['baslik']}'")
                bilesenler = []
            else:
                bilesenler = [dict(b) for b in s["bilesenler"]]
                if s["kodlar"] and k["kod"] not in s["kodlar"]:
                    uyarilar.append(f"{k['kod']} başlıkla eşleşti ama tablo satırındaki kodlar farklı: "
                                    f"{sorted(s['kodlar'])}")
            harfler = [b["harf"] for b in bilesenler]
            if s is not None and not harfler:
                # Görsel olarak doğrulandı: bu satırlarda 9. Tablo'nun sol sütununda yalnızca başlık var.
                notlar.add(f"{k['kod']} ({k['baslik']}): programın 9. Tablosunda süreç bileşeni "
                           f"verilmemiş, yalnızca açıklama var. Eşleştirmede bileşen yazılmaz.")
            elif harfler and harfler != list(TR_ALFABE[: len(harfler)]):
                if harfler == list("abcd"[: len(harfler)]):
                    notlar.add(f"{k['kod']}: PDF'te bileşen harfleri {', '.join(harfler)} "
                               f"(ç atlanmış); PDF'teki gibi korundu.")
                else:
                    uyarilar.append(f"{k['kod']} bileşen sırası beklenmedik: {harfler}")
            ciktilar.append({
                "kod": k["kod"],
                "beceri_alani": BECERILER[k["kod"].split(".")[1]],
                # 9. Tablo'daki başlık tam metindir; tema sayfasında satır sonu kesilebiliyor.
                "metin": s["baslik"] if s else k["baslik"],
                "sayfa": k["sayfa"],
                "tablo9_sayfa": s["sayfa"] if s else None,
                "surec_bilesenleri": bilesenler,
            })
        if t["pdf_sira"] in beklenen and beklenen[t["pdf_sira"]] != len(ciktilar):
            uyarilar.append(f"{t['pdf_sira']}. tema çıktı sayısı tabloda {beklenen[t['pdf_sira']]}, "
                            f"ayrıştırmada {len(ciktilar)}")
        cikti_temalar.append({"islenis_sirasi": t["pdf_sira"], "ad": t["ad"],
                              "ders_saati": t["ders_saati"], "sayfa": t["sayfa"],
                              "ciktilar": ciktilar})

    veri = {
        "ders": "Türkçe",
        "sinif": sinif,
        "kaynak_pdf": PDF,
        "not": ("sayfa alanları PDF sayfa numarasıdır. Türkçe'de aynı öğrenme çıktısı birden fazla "
                "temada yer alabilir; süreç bileşenleri 9. Tablo'dan alınmıştır."),
        "kaynak_notlari": sorted(notlar),
        "temalar": cikti_temalar,
    }
    cikis = os.path.join(kok, "skill", "tymm-surec-eslestirme", "referans", "turkce", f"{sinif}.json")
    os.makedirs(os.path.dirname(cikis), exist_ok=True)
    with open(cikis, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
        f.write("\n")
    toplam = sum(len(t["ciktilar"]) for t in cikti_temalar)
    tekil = len({c["kod"] for t in cikti_temalar for c in t["ciktilar"]})
    print(f"Türkçe {sinif}: {len(cikti_temalar)} tema, {toplam} tema-çıktı ({tekil} tekil kod), "
          f"9. Tablo'da {len(satirlar)} satır -> {os.path.relpath(cikis, kok)}")
    for b in sorted(bilgiler):
        print("  BİLGİ:", b)
    for u in uyarilar:
        print("  UYARI:", u)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
