"""Program PDF'inin metin çıktısından referans JSON'u üretir (Matematik, Fen, Sosyal, İngilizce).

Türkçe programının yapısı farklıdır; onun için scripts/referans_turkce.py kullanılır.

Kullanım:
    pdftotext -enc UTF-8 -layout "<program.pdf>" tmp/pdf-metin/<ad>.txt
    .venv/Scripts/python.exe -I scripts/referans_cikar.py <ders> <sınıf>
    ör.: ... scripts/referans_cikar.py fen-bilimleri 5

Çıktı: skill/tymm-surec-eslestirme/referans/<ders>/<sınıf>.json
Mevcut dosyada `plan_haftalari`/`plan` varsa korunmaz; ardından scripts/plan_haftalari.py çalıştırılır.
"""
import json
import os
import re
import sys

TR_ALFABE = "abcçdefgğhıijklmnoöprsştuüvyz"
EN_ALFABE = "abcdefghijklmnopqrstuvwxyz"

DERSLER = {
    "matematik": {
        "ad": "Matematik", "onek": "MAT", "txt": "ortaokul-matematik-dersi.txt",
        "pdf": "ortaokul-matematik-dersi_20260902_111111_630 (2).pdf", "alfabe": TR_ALFABE,
    },
    "fen-bilimleri": {
        "ad": "Fen Bilimleri", "onek": "FB", "txt": "fen-bilimleri-dersi.txt",
        "pdf": "fen-bilimleri-dersi_20260902_111309_119.pdf", "alfabe": TR_ALFABE,
    },
    "sosyal-bilgiler": {
        "ad": "Sosyal Bilgiler", "onek": "SB", "txt": "sosyal-bilgiler-dersi.txt",
        "pdf": "sosyal-bilgiler-dersi_20260902_111029_619.pdf", "alfabe": TR_ALFABE,
    },
    "ingilizce": {
        "ad": "İngilizce", "onek": "ENG", "txt": "ingilizce-dersi-2-8.txt",
        "pdf": "ingilizce-dersi-2-8.pdf", "alfabe": EN_ALFABE,
    },
}

BASLANGIC_ETIKETLERI = ("ÖĞRENME ÇIKTILARI", "VE SÜREÇ BİLEŞENLERİ",
                        "LEARNING OUTCOMES and PROCESS COMPONENTS")
BITIS_ETIKETLERI = ("İÇERİK ÇERÇEVESİ", "CONTENT FRAME")
SAYFA_BASLIGI_RE = re.compile(r"DERSİ ÖĞRETİM PROGRAMI|THE ENGLISH LANGUAGE CURRICULUM")
TEMA_RE = re.compile(
    r"^\s*(?:(\d+)\.\s*(?:TEMA|ÜNİTE|ÖĞRENME ALANI)\s*:|THEME\s+(\d+)\s*:)\s*(.+?)\s*$")
SAAT_RE = re.compile(r"DERS SAATİ\s+(\d+)")
BILESEN_RE = re.compile(r"^([a-zçğıöşü])\)\s*(.+)$")


def satirlari_oku(yol):
    """(pdf_sayfa, satır) çiftleri. Sayfalar form feed (\\f) ile ayrılır."""
    metin = open(yol, encoding="utf-8").read()
    # PDF'teki kontrol karakterlerini temizle (ör. "S\x07 tudents" -> "Students").
    metin = re.sub(r"\x07\s*", "", metin)
    metin = re.sub(r"[\x00-\x08\x0b\x0e-\x1f]", "", metin)
    for sayfa_no, sayfa in enumerate(metin.split("\f"), start=1):
        for satir in sayfa.split("\n"):
            yield sayfa_no, satir.replace("\t", " ").rstrip()


def birlestir(parcalar):
    """Satır parçalarını birleştirir; satır sonu tirelemesini kaldırır."""
    sonuc = ""
    for p in parcalar:
        p = p.strip()
        if not p:
            continue
        if sonuc.endswith("-") and not sonuc.endswith(" -"):
            sonuc = sonuc[:-1] + p
        elif sonuc:
            sonuc += " " + p
        else:
            sonuc = p
    return re.sub(r"\s+", " ", sonuc)


def kod_deseni(onek, sinif):
    """Öğrenme çıktısı kodu. PDF'teki yazım hatalarına toleranslı: 'ENG5.7.L1.', 'ENG.5.8.R 4.'.
    Gruplar: 1 = ham kod, 2 = tema no, 3 = beceri harfi (yalnız İngilizce), 4 = sıra no, 5 = metin."""
    return re.compile(
        rf"({onek}\.?\s*{sinif}\.\s*(\d+)\.\s*([A-Z]?)\s*(\d+)\.)\s*([^\s\d].*)$")


def standart_kod(onek, sinif, m):
    return f"{onek}.{sinif}.{m.group(2)}.{m.group(3)}{m.group(4)}."


def ayristir(satirlar, onek, sinif):
    kod_re = kod_deseni(onek, sinif)
    temalar, tema = [], None
    blokta = False
    etiket_geri_sayim = 0
    cikti = hedef = None

    def cikti_kapat():
        nonlocal cikti
        if cikti is not None:
            cikti["metin"] = birlestir(cikti.pop("_parca"))
            for b in cikti["surec_bilesenleri"]:
                b["metin"] = birlestir(b.pop("_parca"))
            tema["ciktilar"].append(cikti)
            cikti = None

    for sayfa, s in satirlar:
        if not blokta:
            m = TEMA_RE.match(s)
            if m:
                tema = {"pdf_sira": int(m.group(1) or m.group(2)), "ad": m.group(3).strip(),
                        "ders_saati": None, "ciktilar": [], "sayfa": sayfa}
                temalar.append(tema)
                continue
            if tema is not None and tema["ders_saati"] is None:
                m = SAAT_RE.search(s)
                if m:
                    tema["ders_saati"] = int(m.group(1))
                    continue
            if tema is None:
                continue
            if any(e in s for e in BASLANGIC_ETIKETLERI):
                etiket_geri_sayim = 5
            km = kod_re.search(s)
            if km and etiket_geri_sayim > 0:
                blokta = True
            else:
                if s.strip():
                    etiket_geri_sayim = max(0, etiket_geri_sayim - 1)
                continue

        if any(e in s for e in BITIS_ETIKETLERI):
            cikti_kapat()
            blokta = False
            etiket_geri_sayim = 0
            continue

        temiz = s
        for e in BASLANGIC_ETIKETLERI:
            temiz = temiz.replace(e, " ")
        temiz = temiz.strip()
        if not temiz or temiz.isdigit() or SAYFA_BASLIGI_RE.search(temiz):
            continue

        m = kod_re.search(temiz)
        if m and temiz.startswith(m.group(1)):
            cikti_kapat()
            cikti = {"kod": standart_kod(onek, sinif, m), "_parca": [m.group(5)], "sayfa": sayfa,
                     "surec_bilesenleri": []}
            hedef = cikti["_parca"]
            continue
        m = BILESEN_RE.match(temiz)
        if m and cikti is not None:
            b = {"harf": m.group(1), "_parca": [m.group(2)]}
            cikti["surec_bilesenleri"].append(b)
            hedef = b["_parca"]
            continue
        if hedef is not None:
            hedef.append(temiz)

    return [t for t in temalar if t["ciktilar"]]


BOSLUKSUZ_RE = re.compile(r"[^\s]{35,}")

# Kaynak PDF'te öğrenme çıktıları listesinde bulunmayan ama kodu başka bölümlerde geçen çıktılar.
# Uydurulmaz; yalnızca not düşülür.
KAYNAK_NOTLARI = {
    ("ingilizce", 7): [
        "DİKKAT: 2026-2027 MEB taslak yıllık planının 7. sınıf İngilizce sayfası TYMM'ye değil eski "
        "programa göre hazırlanmış (E7.1.L1 gibi kodlar, 'Appearance and Personality' gibi üniteler). "
        "7. sınıf İngilizce denemeleri bu yıl eski programa göre hazırlanmış olabilir; TYMM ENG.7 "
        "kodlarıyla eşleştirmeden önce kullanıcıya sor. plan_haftalari bu yüzden boş.",
        "ENG.7.5.W7. öğrenme çıktıları listesinde yok (W6'dan sonra S1 geliyor); kod yalnızca "
        "öğrenme-öğretme uygulamaları bölümünde geçiyor. Programda bulunamadı.",
    ],
}


def bosluklari_onar(temalar, pdf_yolu):
    """pdftotext'in boşluklarını kaybettiği çıktı metinlerini PyMuPDF ile yeniden okur."""
    bozuk = [c for t in temalar for c in t["ciktilar"] if BOSLUKSUZ_RE.search(c["metin"])]
    if not bozuk:
        return []
    import pymupdf
    metin = "\n".join(s.get_text() for s in pymupdf.open(pdf_yolu))
    onarilan = []
    for c in bozuk:
        i = metin.find(c["kod"])
        if i < 0:
            continue
        parca = metin[i + len(c["kod"]):].split("\na)")[0]
        yeni = birlestir(parca.split("\n"))
        if yeni and not BOSLUKSUZ_RE.search(yeni):
            onarilan.append(f"{c['kod']} metni PyMuPDF ile onarıldı: {yeni}")
            c["metin"] = yeni
    return onarilan


def mat_tema_tablosu(satirlar, sinif):
    """Yalnızca Matematik: PDF başındaki '<sinif>. SINIF MATEMATİK DERSİ' tablosu."""
    # İşleniş sırası numarası bazı satırlarda eksik olabilir; o zaman bir öncekinden türetilir.
    satir_re = re.compile(
        rf"^\s*(\d+)?\s+(MAT\.{sinif}\.\d+\.)\s*(.+?)\s{{2,}}(\d+)\s+(\d+)\s+(\d+)\s*$")
    tablo, icinde = [], False
    for _, s in satirlar:
        if re.search(rf"^\s*{sinif}\. SINIF MATEMATİK DERSİ\s*$", s):
            icinde = True
            continue
        if icinde:
            m = satir_re.match(s)
            if m:
                sira = int(m.group(1)) if m.group(1) else (tablo[-1]["islenis_sirasi"] + 1 if tablo else 1)
                tablo.append({"islenis_sirasi": sira, "onek": m.group(2), "ad": m.group(3).strip(),
                              "cikti_sayisi": int(m.group(4)), "ders_saati": int(m.group(5))})
            elif "TOPLAM" in s:
                break
    return tablo


def denetle(temalar, alfabe, tablo=None):
    uyarilar = []
    kodlar = [c["kod"] for t in temalar for c in t["ciktilar"]]
    for k in sorted({k for k in kodlar if kodlar.count(k) > 1}):
        uyarilar.append(f"{k} birden fazla kez ayrıştırıldı")
    for t in temalar:
        for c in t["ciktilar"]:
            harfler = [b["harf"] for b in c["surec_bilesenleri"]]
            if not harfler:
                uyarilar.append(f"{c['kod']} hiç süreç bileşeni yok")
            elif harfler != list(alfabe[: len(harfler)]):
                uyarilar.append(f"{c['kod']} bileşen sırası beklenmedik: {harfler}")
            if c["metin"].endswith("-"):
                uyarilar.append(f"{c['kod']} metni tire ile bitiyor")
            for metin in [c["metin"]] + [b["metin"] for b in c["surec_bilesenleri"]]:
                if BOSLUKSUZ_RE.search(metin):
                    uyarilar.append(f"{c['kod']} boşluksuz metin: {metin[:60]}")
    if tablo is not None:
        if len(tablo) != len(temalar):
            uyarilar.append(f"Tema sayısı tabloda {len(tablo)}, ayrıştırmada {len(temalar)}")
        for t in temalar:
            # Tema kodu (ör. MAT.6.2.) ile eşleştir; aynı koda ait bölünmüş temalarda
            # (ör. "(1)", "(2)") parantez içindeki numarayla ayır.
            onek = ".".join(t["ciktilar"][0]["kod"].split(".")[:3]) + "."
            eslesen = [r for r in tablo if r["onek"] == onek]
            if len(eslesen) > 1:
                parca = re.search(r"\(\d\)", t["ad"])
                eslesen = [r for r in eslesen if parca and parca.group(0) in r["ad"]]
            if len(eslesen) != 1:
                uyarilar.append(f"'{t['ad']}' tema tablosunda bulunamadı")
                continue
            r = eslesen[0]
            t["islenis_sirasi"] = r["islenis_sirasi"]
            if r["cikti_sayisi"] != len(t["ciktilar"]):
                uyarilar.append(f"'{t['ad']}' çıktı sayısı tabloda {r['cikti_sayisi']}, "
                                f"ayrıştırmada {len(t['ciktilar'])}")
            if r["ders_saati"] != t["ders_saati"]:
                uyarilar.append(f"'{t['ad']}' ders saati tabloda {r['ders_saati']}, "
                                f"tema sayfasında {t['ders_saati']}")
    return uyarilar


def main():
    ders, sinif = sys.argv[1], int(sys.argv[2])
    ayar = DERSLER[ders]
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    satirlar = list(satirlari_oku(os.path.join(kok, "tmp", "pdf-metin", ayar["txt"])))
    temalar = ayristir(satirlar, ayar["onek"], sinif)
    bilgiler = bosluklari_onar(
        temalar, os.path.join(kok, "tymm_programmes", "pdf_files", ayar["pdf"]))
    tablo = mat_tema_tablosu(satirlar, sinif) if ders == "matematik" else None
    uyarilar = denetle(temalar, ayar["alfabe"], tablo)
    for i, t in enumerate(temalar, start=1):
        t.setdefault("islenis_sirasi", i)  # Matematik dışı: PDF'teki sıra
    temalar.sort(key=lambda t: t["islenis_sirasi"])

    veri = {
        "ders": ayar["ad"],
        "sinif": sinif,
        "kaynak_pdf": ayar["pdf"],
        "not": "sayfa alanları PDF sayfa numarasıdır.",
        "kaynak_notlari": KAYNAK_NOTLARI.get((ders, sinif), []),
        "temalar": [
            {k: t[k] for k in ("islenis_sirasi", "ad", "ders_saati", "sayfa", "ciktilar")}
            for t in temalar
        ],
    }
    cikis = os.path.join(kok, "skill", "tymm-surec-eslestirme", "referans", ders, f"{sinif}.json")
    os.makedirs(os.path.dirname(cikis), exist_ok=True)
    with open(cikis, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
        f.write("\n")
    toplam = sum(len(t["ciktilar"]) for t in temalar)
    print(f"{ayar['ad']} {sinif}: {len(temalar)} tema, {toplam} öğrenme çıktısı -> {os.path.relpath(cikis, kok)}")
    for b in bilgiler:
        print("  BİLGİ:", b)
    for n in veri["kaynak_notlari"]:
        print("  KAYNAK NOTU:", n)
    for u in uyarilar:
        print("  UYARI:", u)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
