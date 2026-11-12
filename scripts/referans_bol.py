"""Büyük referans dosyalarını böler (Türkçe ve İngilizce).

Skill önce küçük ana dosyayı (`<sınıf>.json`) okur, aday öğrenme çıktılarını seçer; süreç
bileşenlerine ihtiyaç duyunca yalnızca ilgili parça dosyasını açar. Böylece bağlam boşa harcanmaz.

Türkçe (aynı çıktı birden fazla temada geçer):
  ana dosya: temalar[].kodlar (yalnızca kod listesi) + ciktilar[] (her kod bir kez:
             kod, beceri_alani, metin, plan_haftalari, bilesen_dosyasi)
  parçalar : <sınıf>/dinleme-izleme.json, okuma.json, konusma.json, yazma.json
İngilizce (çıktı metinleri uzun, temaya özgü):
  ana dosya: temalar[] (ad, ders_saati, plan_haftalari, bilesen_dosyasi, kodlar)
  parçalar : <sınıf>/tema-1.json … tema-8.json (çıktı metni + süreç bileşenleri)

Kullanım:
    .venv/Scripts/python.exe -I scripts/referans_bol.py <ders> <sınıf>
Önce referans_cikar.py / referans_turkce.py ve plan_haftalari.py çalıştırılmış olmalı.
"""
import json
import os
import shutil
import sys

TR_PARCA = {"Dinleme/İzleme": "dinleme-izleme", "Okuma": "okuma", "Konuşma": "konusma", "Yazma": "yazma"}


def yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
        f.write("\n")


def main():
    ders, sinif = sys.argv[1], int(sys.argv[2])
    if ders not in ("turkce", "ingilizce"):
        return
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref = os.path.join(kok, "skill", "tymm-surec-eslestirme", "referans", ders)
    ana_yol = os.path.join(ref, f"{sinif}.json")
    veri = json.load(open(ana_yol, encoding="utf-8"))
    if any("ciktilar" not in t for t in veri["temalar"]):
        raise SystemExit(f"{ana_yol} zaten bölünmüş; önce referansı yeniden üret.")

    klasor = os.path.join(ref, str(sinif))
    shutil.rmtree(klasor, ignore_errors=True)
    os.makedirs(klasor)
    ust = {k: veri[k] for k in ("ders", "sinif", "kaynak_pdf", "not", "kaynak_notlari")}
    ust["not"] += " Süreç bileşenleri `bilesen_dosyasi` alanındaki dosyadadır (bu klasöre göre)."

    if ders == "turkce":
        ciktilar, parcalar = {}, {}
        for t in veri["temalar"]:
            for c in t["ciktilar"]:
                ad = TR_PARCA[c["beceri_alani"]]
                ciktilar.setdefault(c["kod"], {
                    "kod": c["kod"], "beceri_alani": c["beceri_alani"], "metin": c["metin"],
                    "plan_haftalari": c.get("plan_haftalari", []),
                    "bilesen_dosyasi": f"{sinif}/{ad}.json"})
                parcalar.setdefault(ad, {})[c["kod"]] = {
                    "kod": c["kod"], "metin": c["metin"], "tablo9_sayfa": c["tablo9_sayfa"],
                    "surec_bilesenleri": c["surec_bilesenleri"]}
            t["kodlar"] = [c["kod"] for c in t.pop("ciktilar")]
        ana = {**ust, "plan": veri.get("plan"), "temalar": veri["temalar"],
               "ciktilar": sorted(ciktilar.values(), key=lambda c: c["kod"])}
    else:
        parcalar = {}
        for t in veri["temalar"]:
            ad = f"tema-{t['islenis_sirasi']}"
            parcalar[ad] = {c["kod"]: {k: c[k] for k in ("kod", "metin", "sayfa", "surec_bilesenleri")}
                            for c in t["ciktilar"]}
            t["plan_haftalari"] = sorted({h for c in t["ciktilar"] for h in c.get("plan_haftalari", [])})
            t["bilesen_dosyasi"] = f"{sinif}/{ad}.json"
            t["kodlar"] = [c["kod"] for c in t.pop("ciktilar")]
        ana = {**ust, "beceri_harfleri": {"L": "Listening", "R": "Reading", "S": "Speaking",
                                          "W": "Writing", "V": "Vocabulary", "G": "Grammar",
                                          "P": "Pronunciation"},
               "plan": veri.get("plan"), "temalar": veri["temalar"]}

    for ad, kodlar in parcalar.items():
        yaz(os.path.join(klasor, f"{ad}.json"),
            {"ders": veri["ders"], "sinif": sinif, "parca": ad,
             "ciktilar": sorted(kodlar.values(), key=lambda c: c["kod"])})
    yaz(ana_yol, ana)
    print(f"{ders} {sinif}: ana dosya + {len(parcalar)} parça")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
