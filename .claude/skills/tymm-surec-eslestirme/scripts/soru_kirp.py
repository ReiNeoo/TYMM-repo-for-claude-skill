"""Taranmış ya da metin katmanlı kitapçık PDF'inden soruları tek tek kırpar.

İki adım:

1) Bloklar — sayfaları sütun ve boşluklara göre içerik bloklarına ayırır, numaralı önizleme üretir:
    python -I soru_kirp.py bloklar <kitapçık.pdf> <klasör> [--sayfalar 3-9]
   Çıktı: <klasör>/onizleme/sNN.png (blok kutuları ve kimlikleri çizili), <klasör>/bloklar.json
   Blok kimliği: "<sayfa>.<sıra>" (ör. "03.4"); sıra sol sütun yukarıdan aşağı, sonra sağ sütun.

2) Kes — harita.json'a göre her soruyu tek PNG olarak keser:
    python -I soru_kirp.py kes <kitapçık.pdf> <klasör>/bloklar.json <harita.json> <çıkış klasörü>
   harita.json: {"matematik-03": ["03.2", "03.3", "03.4"], ...}
     - Liste ögesi bir blok kimliği ya da "03.2-03.5" aralığı (aynı sayfa) olabilir.
     - Otomatik bölme yetmezse elle bölge: {"sayfa": 3, "kutu": [x0, y0, x1, y1]} (0–1 oranları).
     - Ortak kök/görsel ("3 ve 4. soruları…") her iki sorunun listesine de yazılır.
   Bölgeler sırayla alt alta dizilir; çıktı <çıkış>/<anahtar>.png.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pymupdf  # noqa: E402

import ortak  # noqa: E402

UZUN_KENAR = 1600  # bölme için çizim çözünürlüğü (px)
MUREKKEP = 200     # bu griden koyu pikseller içerik sayılır


def sayfa_araligi(metin, n):
    if not metin:
        return list(range(1, n + 1))
    sonuc = []
    for parca in metin.split(","):
        if "-" in parca:
            a, b = parca.split("-")
            sonuc += range(int(a), int(b) + 1)
        else:
            sonuc.append(int(parca))
    return sonuc


def gri(sayfa, olcek):
    pix = sayfa.get_pixmap(matrix=pymupdf.Matrix(olcek, olcek), colorspace=pymupdf.csGRAY, alpha=False)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)


def kosular(maske, min_bosluk):
    """Doğru/yanlış dizisinde, aralarında en az min_bosluk boşluk olan 'doğru' koşularını döndürür."""
    idx = np.flatnonzero(maske)
    if idx.size == 0:
        return []
    sonuc, bas, onceki = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - onceki > min_bosluk:
            sonuc.append((bas, onceki + 1))
            bas = i
        onceki = i
    sonuc.append((bas, onceki + 1))
    return sonuc


def ayrac_bul(m):
    """İki sütunlu sayfada sütun arası şeridi bulur.

    m: mürekkep maskesi. Dönüş: (x0, x1, ayrac_sutunlari) ya da None (tek sütun).
    Şeritte ince bir ayraç çizgisi (düz/noktalı) olabilir; pencere içindeki en yoğun birkaç piksel
    sütunu çizgi sayılır. Başlık gibi tam genişlikteki satırlar şeridi keser; şerit, mürekkepli
    satırların çoğunda boşsa kabul edilir."""
    h, w = m.shape
    govde = m[int(h * 0.05):int(h * 0.95)]
    murekkepli = govde.any(axis=1).sum()
    if murekkepli == 0:
        return None
    pencere = max(10, int(w * 0.015))
    adaylar = []
    for x in range(int(w * 0.38), int(w * 0.62) - pencere):
        alt = govde[:, x:x + pencere]
        yogunluk = alt.sum(axis=0)
        cizgi = np.argsort(yogunluk)[-6:]
        cizgi = cizgi[yogunluk[cizgi] > 0]
        tut = np.setdiff1d(np.arange(pencere), cizgi)
        kesiyor = alt[:, tut].sum(axis=1) > 1
        # Hem solunda hem sağında mürekkep olan satırlar arasında şeridin kesintisiz boş kaldığı
        # en uzun dizi. Tek sütunlu sayfada kelime boşlukları satırdan satıra kaydığı için kısa kalır.
        iki_yan = govde[:, :x].any(axis=1) & govde[:, x + pencere:].any(axis=1)
        dizi = ~kesiyor[iki_yan]
        en_uzun = max((b - a for a, b in kosular(dizi, 1)), default=0)
        adaylar.append((en_uzun, int(kesiyor.sum()), x, x + cizgi))
    if not adaylar:
        return None
    en_uzun = max(c[0] for c in adaylar)
    if en_uzun < h * 0.12:
        return None
    # Eşit derecede uzun boş dizi veren pencerelerden en az kesilenleri al, onların ortasını seç
    # (pencere sütun içeriğinin kenarına yapışmasın).
    iyiler = [c for c in adaylar if c[0] >= en_uzun * 0.9]
    en_az = min(c[1] for c in iyiler)
    iyiler = [c for c in iyiler if c[1] == en_az]
    _, _, x0, cizgi = iyiler[len(iyiler) // 2]
    x1 = x0 + pencere
    # Her iki yanda da kayda değer içerik olmalı.
    if govde[:, :x0].sum() < murekkepli or govde[:, x1:].sum() < murekkepli:
        return None
    return x0, x1, cizgi


def tight_kutu(m, y0, y1, x0, x1):
    xs = np.flatnonzero(m[y0:y1, x0:x1].any(axis=0))
    return (x0 + xs[0], y0, x0 + xs[-1] + 1, y1)


def bloklar_cikar(g):
    h, w = g.shape
    m = g < MUREKKEP
    min_bosluk = max(6, int(h * 0.012))
    ayrac = ayrac_bul(m)
    if ayrac is None:
        satir = m.sum(axis=1) > 1
        return [tight_kutu(m, y0, y1, 0, w) for y0, y1 in kosular(satir, min_bosluk) if y1 - y0 >= 4]

    x0, x1, cizgi = ayrac
    m = m.copy()
    # Ayraç çizgisini tüm sayfa boyunca sil (noktalı çizgi kalıntısı blok oluşturmasın).
    for c in cizgi:
        dikey = m[:, max(0, c - 1):c + 2].any(axis=1)
        if dikey.sum() > h * 0.2:
            m[:, max(0, c - 1):c + 2] = False
    # Şeridi kesen satırlar tam genişlikte içeriktir (başlık, yönerge, geniş görsel).
    kesen = m[:, x0:x1].sum(axis=1) > 1
    sonuc = []
    for y0, y1 in kosular(kesen, min_bosluk):
        if y1 - y0 >= 4:
            sonuc.append(tight_kutu(m, y0, y1, 0, w))
    tam = np.zeros(h, dtype=bool)
    for _, y0, _, y1 in sonuc:
        tam[y0:y1] = True
    orta = (x0 + x1) // 2
    for sx0, sx1 in ((0, orta), (orta, w)):
        parca = m[:, sx0:sx1].copy()
        parca[tam] = False
        satir = parca.sum(axis=1) > 1
        for y0, y1 in kosular(satir, min_bosluk):
            if y1 - y0 >= 4:
                sonuc.append(tight_kutu(parca, y0, y1, 0, sx1 - sx0))
                k = sonuc[-1]
                sonuc[-1] = (k[0] + sx0, k[1], k[2] + sx0, k[3])
    # Sıra: tam genişlik blokları ve sütunlar okuma sırasına göre — önce y'ye göre bantlar,
    # bant içinde sol sütun sonra sağ sütun.
    tam_bloklar = sorted([b for b in sonuc if b[0] < orta < b[2] and b[2] - b[0] > w * 0.5], key=lambda b: b[1])
    sutun_bloklari = [b for b in sonuc if b not in tam_bloklar]
    sirali, onceki_y = [], 0
    for tb in tam_bloklar + [(0, h, w, h)]:
        bant = [b for b in sutun_bloklari if onceki_y <= b[1] < tb[1]]
        sirali += sorted(bant, key=lambda b: (b[0] >= orta, b[1]))
        if tb[1] < h:
            sirali.append(tb)
        onceki_y = tb[3]
    return sirali


def komut_bloklar(a):
    doc = pymupdf.open(a.pdf)
    os.makedirs(os.path.join(a.klasor, "onizleme"), exist_ok=True)
    kayit = {"pdf": os.path.abspath(a.pdf), "sayfalar": {}}
    for no in sayfa_araligi(a.sayfalar, doc.page_count):
        sayfa = doc[no - 1]
        r = sayfa.rect
        olcek = UZUN_KENAR / max(r.width, r.height)
        g = gri(sayfa, olcek)
        kutular = bloklar_cikar(g)
        liste = {}
        for i, (x0, y0, x1, y1) in enumerate(kutular, start=1):
            liste[f"{no:02d}.{i}"] = [round(v / olcek, 1) for v in (x0, y0, x1, y1)]  # PDF koordinatı
        kayit["sayfalar"][str(no)] = {"genislik": r.width, "yukseklik": r.height, "bloklar": liste}

        # Önizleme: kutuları ve kimlikleri sayfa kopyasına çiz.
        gecici = pymupdf.open()
        gecici.insert_pdf(doc, from_page=no - 1, to_page=no - 1)
        p = gecici[0]
        p.clean_contents()
        for kimlik, kutu in liste.items():
            rr = pymupdf.Rect(kutu) + (-2, -2, 2, 2)
            p.draw_rect(rr, color=(0.9, 0.1, 0.1), width=0.8)
            etiket = kimlik.split(".")[1]
            ex = max(0, rr.x0 - 6 - 6 * len(etiket))
            p.draw_rect(pymupdf.Rect(ex, rr.y0, ex + 4 + 6 * len(etiket), rr.y0 + 12),
                        color=(0.9, 0.1, 0.1), fill=(0.9, 0.1, 0.1))
            p.insert_text((ex + 2, rr.y0 + 9.5), etiket, fontsize=10, color=(1, 1, 1))
        p.get_pixmap(matrix=pymupdf.Matrix(olcek, olcek)).save(
            os.path.join(a.klasor, "onizleme", f"s{no:02d}.png"))
        print(f"  s{no:02d}: {len(liste)} blok")
    ortak.yaz(os.path.join(a.klasor, "bloklar.json"), kayit)
    print(f"Önizlemeler: {os.path.join(a.klasor, 'onizleme')}")


def bolgeler(oge, kayit):
    """Harita ögesi -> [(sayfa_no, Rect, kimlik|None)]"""
    if isinstance(oge, dict):
        s = kayit["sayfalar"].get(str(oge["sayfa"]))
        if s is None:
            raise SystemExit(f"bloklar.json'da sayfa {oge['sayfa']} yok")
        x0, y0, x1, y1 = oge["kutu"]
        return [(oge["sayfa"], pymupdf.Rect(x0 * s["genislik"], y0 * s["yukseklik"],
                                             x1 * s["genislik"], y1 * s["yukseklik"]), None)]
    if "-" in oge:
        bas, son = oge.split("-")
        sayfa, i = bas.split(".")
        _, j = son.split(".")
        kimlikler = [f"{sayfa}.{k}" for k in range(int(i), int(j) + 1)]
    else:
        kimlikler = [oge]
    sonuc = []
    for k in kimlikler:
        sayfa = int(k.split(".")[0])
        try:
            sonuc.append((sayfa, pymupdf.Rect(kayit["sayfalar"][str(sayfa)]["bloklar"][k]), k))
        except KeyError:
            raise SystemExit(f"blok bulunamadı: {k}")
    return sonuc


def birlestir(liste, kayit):
    """Bir sorunun bloklarını, sayfadaki başka bir bloğu içine almadığı sürece birleştirir.

    Böylece yan yana seçenekler ve ardışık parçalar tek dikdörtgen olur; sütun değiştiren ya da
    arada başka sorunun bulunduğu parçalar ayrı bölge kalır. Sıra: sayfa, sonra okuma sırası."""
    sayfalar = []
    for sayfa, _, _ in liste:
        if sayfa not in sayfalar:
            sayfalar.append(sayfa)
    sonuc = []
    for sayfa in sayfalar:
        secili = [(r, k) for s, r, k in liste if s == sayfa]
        kimlikler = {k for _, k in secili if k}
        digerleri = [pymupdf.Rect(v) for k, v in kayit["sayfalar"][str(sayfa)]["bloklar"].items()
                     if k not in kimlikler]
        rects = [pymupdf.Rect(r) for r, _ in secili]

        def yutar(u):
            return any((u & o).get_area() > 0.2 * max(o.get_area(), 1) for o in digerleri)

        degisti = True
        while degisti:
            degisti = False
            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    u = rects[i] | rects[j]
                    if not yutar(u):
                        rects[i] = u
                        del rects[j]
                        degisti = True
                        break
                if degisti:
                    break
        genislik = kayit["sayfalar"][str(sayfa)]["genislik"]
        rects.sort(key=lambda r: (r.x0 >= genislik / 2 and r.width < genislik * 0.6, r.y0))
        sonuc += [(sayfa, r) for r in rects]
    return sonuc


def komut_kes(a):
    doc = pymupdf.open(a.pdf)
    kayit = ortak.oku(a.bloklar)
    harita = ortak.oku(a.harita)
    os.makedirs(a.cikis, exist_ok=True)
    pay, ara = 6, 14
    for anahtar, ogeler in harita.items():
        liste = []
        for oge in ogeler:
            liste += bolgeler(oge, kayit)
        liste = birlestir(liste, kayit)
        kirpimlar = []
        for sayfa, r in liste:
            sr = doc[sayfa - 1].rect
            kirpimlar.append((sayfa, (r + (-pay, -pay, pay, pay)) & sr))
        gen = max(r.width for _, r in kirpimlar)
        yuk = sum(r.height for _, r in kirpimlar) + ara * (len(kirpimlar) - 1)
        yeni = pymupdf.open()
        p = yeni.new_page(width=gen, height=yuk)
        y = 0
        for i, (sayfa, r) in enumerate(kirpimlar):
            p.show_pdf_page(pymupdf.Rect(0, y, r.width, y + r.height), doc, sayfa - 1, clip=r)
            y += r.height + ara
            if i < len(kirpimlar) - 1:  # bölgeler arasına ince ayırıcı
                p.draw_line((0, y - ara / 2), (gen, y - ara / 2), color=(0.75, 0.75, 0.75), width=0.5, dashes="[3 3] 0")
        olcek = min(3.0, 1400 / gen)
        p.get_pixmap(matrix=pymupdf.Matrix(olcek, olcek)).save(os.path.join(a.cikis, f"{anahtar}.png"))
        print(f"  {anahtar}.png  ({len(kirpimlar)} bölge)")


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    b = alt.add_parser("bloklar")
    b.add_argument("pdf")
    b.add_argument("klasor")
    b.add_argument("--sayfalar", help="ör. 3-9 veya 2,4,6")
    k = alt.add_parser("kes")
    k.add_argument("pdf")
    k.add_argument("bloklar")
    k.add_argument("harita")
    k.add_argument("cikis")
    a = ap.parse_args()
    komut_bloklar(a) if a.komut == "bloklar" else komut_kes(a)


if __name__ == "__main__":
    ortak.utf8()
    main()
