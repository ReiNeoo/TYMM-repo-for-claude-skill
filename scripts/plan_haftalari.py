"""MEB taslak çerçeve yıllık planındaki haftaları referans JSON'una ekler (tüm dersler).

Kullanım:
    .venv/Scripts/python.exe -I scripts/plan_haftalari.py <ders> <sınıf>
    ör.: ... scripts/plan_haftalari.py fen-bilimleri 5

Önce zip arşivi tmp/plan/<ders>/ altına çıkarılmış olmalı:
    unzip -o "tymm_programmes/taslak_plans/<arşiv>.zip" -d tmp/plan/<ders>

Her öğrenme çıktısına `plan_haftalari` (hafta numaraları) eklenir; JSON'un üst düzeyine `plan`
(kaynak dosya, sayfa ve hafta -> tarih aralığı, plandaki yazımıyla) yazılır.
Kodlar, referanstaki her kod için toleranslı bir desenle aranır (planlardaki "B.5.1.2." gibi
eksik harfli ya da "ENG5.1.L1" gibi noktasız yazımlar yakalanır).
"""
import glob
import json
import os
import re
import sys

import openpyxl

# Planın xlsx dosyası tmp/plan/<klasör>/ altında aranır. Hecce Yayınları dosyası kullanılmaz.
PLANLAR = {
    "matematik": "matematik",
    "fen-bilimleri": "fen-bilimleri",
    "sosyal-bilgiler": "sosyal-bilgiler",
    "ingilizce": "ingilizce",
    "turkce": "ortaokul-turkce",
}
HAFTA_RE = re.compile(r"(?:(\d+)\.\s*Hafta|Week\s*(\d+))\s*:?\s*(.*)", re.S | re.I)


def kod_deseni(kod):
    """'SB.5.1.2.' -> 'S?B\\.?\\s*5\\.\\s*1\\.\\s*2(?!\\d)' benzeri toleranslı desen."""
    parcalar = [p for p in kod.strip(".").split(".")]
    bas = parcalar[0]
    desen = (re.escape(bas[0]) + "?" + re.escape(bas[1:])) if len(bas) > 1 else re.escape(bas)
    for p in parcalar[1:]:
        m = re.fullmatch(r"([A-Z]*)(\d*)", p)  # "5", "L1" (İngilizce), "O" (Türkçe beceri harfi)
        harf = re.escape(m.group(1)) + (r"\s*" if m.group(2) else "") if m.group(1) else ""
        desen += r"\.?\s*" + harf + m.group(2)
    return re.compile(r"(?<![A-Za-z0-9])" + desen + r"(?!\d)")


def sayfa_sec(wb, sinif):
    adaylar = [ws for ws in wb.worksheets if re.search(rf"(?<!\d){sinif}(?!\d)", ws.title)]
    if len(adaylar) != 1:
        raise SystemExit(f"{sinif}. sınıf sayfası belirsiz: {[ws.title for ws in wb.worksheets]}")
    return adaylar[0]


def main():
    ders, sinif = sys.argv[1], int(sys.argv[2])
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dosyalar = [f for f in glob.glob(os.path.join(kok, "tmp", "plan", PLANLAR[ders], "**", "*.xlsx"),
                                     recursive=True) if "Hecce" not in f]
    if len(dosyalar) != 1:
        raise SystemExit(f"Plan dosyası bulunamadı ya da birden fazla: {dosyalar}")
    xlsx = dosyalar[0]
    ws = sayfa_sec(openpyxl.load_workbook(xlsx, data_only=True), sinif)

    json_yolu = os.path.join(kok, "skill", "tymm-surec-eslestirme", "referans", ders, f"{sinif}.json")
    veri = json.load(open(json_yolu, encoding="utf-8"))
    kodlar = sorted({c["kod"] for t in veri["temalar"] for c in t["ciktilar"]})
    desenler = {k: kod_deseni(k) for k in kodlar}

    haftalar, kod_haftalari, hafta = {}, {}, None
    for satir in ws.iter_rows(values_only=True):
        hucreler = ["" if h is None else str(h) for h in satir]
        m = HAFTA_RE.search(hucreler[1]) if len(hucreler) > 1 else None
        if m:
            hafta = int(m.group(1) or m.group(2))
            haftalar[hafta] = re.sub(r"\s+", " ", m.group(3)).strip()
        if hafta is None:
            continue
        metin = "\n".join(hucreler[3:])
        for k, d in desenler.items():
            if d.search(metin):
                kod_haftalari.setdefault(k, set()).add(hafta)

    uyarilar = []
    for t in veri["temalar"]:
        for c in t["ciktilar"]:
            c["plan_haftalari"] = sorted(kod_haftalari.get(c["kod"], []))
    for k in kodlar:
        if k not in kod_haftalari:
            uyarilar.append(f"{k} planda hiç geçmiyor")

    veri["plan"] = {
        "kaynak": os.path.basename(xlsx),
        "sayfa": ws.title.strip(),
        "haftalar": {str(k): v for k, v in sorted(haftalar.items())},
    }
    with open(json_yolu, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{ders} {sinif}: '{ws.title.strip()}' sayfası, {len(haftalar)} hafta, "
          f"{len(kod_haftalari)}/{len(kodlar)} kod planda bulundu")
    for u in uyarilar:
        print("  UYARI:", u)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
