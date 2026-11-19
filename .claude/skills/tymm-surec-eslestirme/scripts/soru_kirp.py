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

Metin katmanlı PDF'lerde harita otomatik çıkarılabilir (1 ile 2 arasında):
    python -I soru_kirp.py harita <kitapçık.pdf> <klasör>/bloklar.json <harita.json>         --ders matematik --sayfalar 18-24 --soru-sayisi 15
   Blokları okuma sırasına dizer (tam genişlik bantlar, sonra sol ve sağ sütun); soru numarasıyla
   ("7.") başlayan blok yeni soruyu açar, numarasız bloklar önceki soruya eklenir; "7, 8 ve 9.
   soruları…" kökü ilgili tüm sorulara yazılır; sayfa başlığı/numarası blokları atlanır. Bir blokta
   iki soru başlıyorsa blok bölünür. Var olan harita dosyasına ekler (aynı ders anahtarları yenilenir).
   Önizlemeyi okumak yerine kırpımları kontrol et; sorunlu soruyu haritada elle düzelt.

Kontrol panosu (kırpımların küçük resimleri tek görselde):
    python -I soru_kirp.py pano <çıkış klasörü> <pano.png> --onek matematik
"""
import re
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


def birlestir(liste, kayit, baskalari=None):
    """Bir sorunun bloklarını, sayfadaki başka bir bloğu içine almadığı sürece birleştirir.
    baskalari verilirse ({sayfa: [Rect]}) yalnızca başka sorulara ait bölgeler engel sayılır; sayfa
    başlığı gibi hiçbir soruya ait olmayan bloklar birleştirmeyi bölmez.

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
        if baskalari is not None:
            kendi = [pymupdf.Rect(r) for r, _ in secili]
            digerleri = [o for o in baskalari.get(sayfa, []) if not any(o == k for k in kendi)]
        else:
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
    if a.bloklar == "-":   # harita-metin çıktısı: yalnızca sayfa boyutları gerekir
        kayit = {"sayfalar": {str(i + 1): {"genislik": p.rect.width, "yukseklik": p.rect.height, "bloklar": {}}
                              for i, p in enumerate(doc)}}
    else:
        kayit = ortak.oku(a.bloklar)
    harita = ortak.oku(a.harita)
    os.makedirs(a.cikis, exist_ok=True)
    pay, ara = 6, 14
    tumu = {k: [b for oge in v for b in bolgeler(oge, kayit)] for k, v in harita.items()}
    for anahtar, liste in tumu.items():
        baskalari = {}
        for diger, bl in tumu.items():
            if diger != anahtar:
                for sayfa, r, _ in bl:
                    baskalari.setdefault(sayfa, []).append(r)
        liste = birlestir(liste, kayit, baskalari)
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


ATLA = ("Diğer sayfaya", "Bu testte", "Cevaplarınızı", "BÖLÜM", "TESTİNE GEÇİNİZ", "KONTROL EDİNİZ",
        "SÜREÇ İZLEME", "ÖRNEKTİR")
BASLIK = re.compile(r"^\d+\.\s*(Sınıf|SINIF)\b")  # sayfa başlığı ("6. Sınıf") soru numarası değildir
KOK = re.compile(r"^(?:Answer the questions\s+)?((?:\d+\s*,\s*)*\d+\s+(?:ve|and)\s+\d+)"
                 r"(?:\s*\.\s*sorular|\s+according)", re.I)
NO = re.compile(r"^(\d{1,2})\.$")


def okuma_sirasi(bloklar, genislik):
    """Blok kimliklerini okuma sırasına dizer: tam genişlik bantlar ayırıcıdır; aralarında önce sol, sonra sağ sütun."""
    orta = genislik / 2
    tam = lambda k: bloklar[k][0] < orta - 60 and bloklar[k][2] > orta + 60  # noqa: E731
    sira, kesit = [], []
    def bosalt():
        sol = sorted((k for k in kesit if bloklar[k][0] + bloklar[k][2] < 2 * orta), key=lambda k: bloklar[k][1])
        sag = sorted((k for k in kesit if k not in sol), key=lambda k: bloklar[k][1])
        sira.extend(sol + sag)
        kesit.clear()
    for k in sorted(bloklar, key=lambda k: bloklar[k][1]):
        if tam(k):
            bosalt()
            sira.append(k)
        else:
            kesit.append(k)
    bosalt()
    return sira


def komut_harita(a):
    doc = pymupdf.open(a.pdf)
    kayit = ortak.oku(a.bloklar)
    harita = ortak.oku(a.harita) if os.path.exists(a.harita) else {}
    harita = {k: v for k, v in harita.items() if not k.startswith(a.ders + "-")}
    yeni, hedef, son = {}, [], 0
    uyarilar = []
    def ekle(nolar, oge):
        for n in nolar:
            yeni.setdefault(n, []).append(oge)
    for no in sayfa_araligi(a.sayfalar, doc.page_count):
        s = kayit["sayfalar"].get(str(no))
        if s is None:
            sys.exit(f"bloklar.json'da sayfa {no} yok; önce 'bloklar' komutunu bu sayfalar için çalıştır")
        sayfa = doc[no - 1]
        # Her kelime, merkezini içeren bloğa; yoksa 25 pt içindeki en yakın bloğa (sütun arası numaralar) atanır.
        kutular = {k: pymupdf.Rect(v) for k, v in s["bloklar"].items()}
        dagilim = {k: [] for k in kutular}
        for w in sayfa.get_text("words"):
            m = pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
            # Sütun boşluğuna taşan soru numarası ("6."): hemen sağında başlayan bloğa aittir.
            sag = [k for k, r in kutular.items() if NO.match(w[4]) and 0 <= r.x0 - w[2] <= 25
                   and r.y0 - 15 <= w[3] and r.y1 >= w[1]] if NO.match(w[4]) else []
            if sag:
                dagilim[min(sag, key=lambda k: kutular[k].y0)].append(w)
                continue
            uzak = {k: (0 if r.contains(m) else
                        ((max(r.x0 - m.x, 0, m.x - r.x1)) ** 2 + (max(r.y0 - m.y, 0, m.y - r.y1)) ** 2) ** 0.5)
                    for k, r in kutular.items()}
            k = min(uzak, key=uzak.get) if uzak else None
            if k is not None and uzak[k] <= 25:
                dagilim[k].append(w)
        # Sütunların sol kenarı: o sütundaki "N." adaylarının en soldaki x'i. Soru numarası bu kenarda
        # durur; madde listelerindeki "1. … 5." gibi numaralar içeride kaldığı için elenir.
        orta = s["genislik"] / 2
        adaylar = [w for v in dagilim.values() for w in v if NO.match(w[4])]
        sol_kenar = min((w[0] for w in adaylar if (w[0] + w[2]) / 2 < orta), default=0)
        sag_kenar = min((w[0] for w in adaylar if (w[0] + w[2]) / 2 >= orta), default=orta)
        for kimlik in okuma_sirasi(s["bloklar"], s["genislik"]):
            r = pymupdf.Rect(s["bloklar"][kimlik]) + (-1, -1, 1, 1)
            ws = dagilim[kimlik]
            if ws:  # numara bloğun dışındaysa kutuyu numarayı kapsayacak şekilde genişlet
                r |= pymupdf.Rect(min(w[0] for w in ws), min(w[1] for w in ws),
                                  max(w[2] for w in ws), max(w[3] for w in ws))
            metin = " ".join(w[4] for w in ws)
            if not ws:
                continue
            # Satır başındaki soru numaraları (sütun kenarında; solunda aynı satırda kelime olmayan "N.")
            baslar = []
            for w in ws:
                m = NO.match(w[4])
                kenar = sol_kenar if (w[0] + w[2]) / 2 < orta else sag_kenar
                if m and abs(w[0] - kenar) <= 5 and w[1] > 55 and not any(abs(v[1] - w[1]) < 3 and v[2] <= w[0] + 1 and v[0] < w[0] - 1
                                 and w[0] - v[2] < 6 for v in ws if v is not w):
                    baslar.append((int(m.group(1)), w))
            beklenen = []
            for n, w in sorted(baslar, key=lambda t: (t[1][1], t[1][0])):
                sonraki = (beklenen[-1][0] if beklenen else son) + 1
                if sonraki <= n <= min(sonraki + 1, a.soru_sayisi):  # bir numara kaçırılmışsa yeniden yakala
                    if n > sonraki:
                        uyarilar.append(f"{kimlik}: {sonraki}. soru bulunamadı, {n}. sorudan devam edildi")
                    beklenen.append((n, w))
            # Sayfa başlığı/numarası/yönerge blokları (soru başlatmıyorsa) atlanır.
            if not beklenen and (any(x in metin for x in ATLA) or re.fullmatch(r"[\d\s☞]*", metin)
                                 or re.search(r"\bSINIF\b", metin)):
                continue
            kok = KOK.search(metin)
            if a.ayrinti:
                print(f"    {kimlik} hedef={hedef} son={son} baslar={[n for n, _ in baslar]} "
                      f"beklenen={[n for n, _ in beklenen]} | {metin[:60]}")
            if kok and (not beklenen or kok.start() < metin.find(beklenen[0][1][4])):
                hedef = [int(x) for x in re.findall(r"\d+", kok.group(1))]
                ekle(hedef, kimlik if ayni(r, s["bloklar"][kimlik]) else {"sayfa": no, "kutu": oran(r + (-2, -2, 2, 2), s)})
                continue
            if not beklenen:
                if not hedef:
                    uyarilar.append(f"{kimlik}: soru numarasından önce gelen blok atlandı: {metin[:50]}")
                    continue
                ekle(hedef, kimlik if ayni(r, s["bloklar"][kimlik]) else {"sayfa": no, "kutu": oran(r + (-2, -2, 2, 2), s)})
                continue
            if r.y0 < beklenen[0][1][1] - 25 and hedef:   # bloğun üst kısmı önceki soruya ait
                ust = pymupdf.Rect(r.x0, r.y0, r.x1, beklenen[0][1][1] - 3)
                ekle(hedef, {"sayfa": no, "kutu": oran(ust, s)})
                r = pymupdf.Rect(r.x0, beklenen[0][1][1] - 3, r.x1, r.y1)
            if len(beklenen) == 1:
                ekle([beklenen[0][0]], kimlik if ayni(r, s["bloklar"][kimlik])
                     else {"sayfa": no, "kutu": oran(r + (-2, -2, 2, 2), s)})
            else:
                xs = [w[0] for _, w in beklenen]
                yan = max(xs) - min(xs) > 100
                uyarilar.append(f"{kimlik}: blokta {len(beklenen)} soru başlıyor "
                                f"({', '.join(str(n) for n, _ in beklenen)}); {'dikey' if yan else 'yatay'} bölündü")
                for i, (n, w) in enumerate(beklenen):
                    if yan:
                        x0 = r.x0 if i == 0 else w[0] - 6
                        x1 = r.x1 if i == len(beklenen) - 1 else beklenen[i + 1][1][0] - 6
                        parca = pymupdf.Rect(x0, r.y0, x1, r.y1)
                    else:
                        y1 = r.y1 if i == len(beklenen) - 1 else beklenen[i + 1][1][1] - 3
                        parca = pymupdf.Rect(r.x0, w[1] - 3, r.x1, y1)
                    ekle([n], {"sayfa": no, "kutu": oran(parca, s)})
            son = beklenen[-1][0]
            hedef = [son]
    for n in sorted(yeni):
        harita[f"{a.ders}-{n:02d}"] = yeni[n]
    eksik = [n for n in range(1, a.soru_sayisi + 1) if n not in yeni]
    ortak.yaz(a.harita, harita)
    for u in uyarilar:
        print("  UYARI", u)
    print(f"{a.ders}: {len(yeni)} soru haritalandı" + (f"; EKSİK: {eksik}" if eksik else ""))


def ayni(r, kutu, tolerans=4):
    """Genişletilmiş kutu bloğun kendisinden belirgin farklı değilse blok kimliği kullanılır (birleştirme için)."""
    return all(abs(u - v) <= tolerans for u, v in zip((r.x0, r.y0, r.x1, r.y1), kutu))


def oran(r, s):
    return [round(r.x0 / s["genislik"], 4), round(r.y0 / s["yukseklik"], 4),
            round(r.x1 / s["genislik"], 4), round(r.y1 / s["yukseklik"], 4)]


def komut_harita_metin(a):
    """Metin katmanlı PDF: soru numaralarının konumundan geometrik bölgeler.

    Her soru kendi sütununda numarasından, aynı sütundaki sonraki numaraya (ya da altındaki tam
    genişlik içeriğe / sayfa sonuna) kadar uzanır. Satırı sütun sınırını aşan soru tam genişliktir.
    Ortak kök ("10 ve 11. soruları…") ilk hedef soruya kadar olan bölgeyi bütün hedeflere ekler."""
    doc = pymupdf.open(a.pdf)
    harita = ortak.oku(a.harita) if os.path.exists(a.harita) else {}
    harita = {k: v for k, v in harita.items() if not k.startswith(a.ders + "-")}
    bolge, uyarilar, son, hedef = {}, [], 0, []
    for no in sayfa_araligi(a.sayfalar, doc.page_count):
        sayfa = doc[no - 1]
        W, H = sayfa.rect.width, sayfa.rect.height
        satirlar = []
        for b in sayfa.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                if abs(ln.get("dir", (1, 0))[1]) > 0.05:   # eğik filigran ("ÖRNEKTİR") satırları
                    continue
                t = "".join(sp["text"] for sp in ln["spans"]).strip()
                r = pymupdf.Rect(ln["bbox"])
                if t and not (any(x in t for x in ATLA) or re.search(r"\bSINIF\b", t) or BASLIK.match(t)
                              or re.fullmatch(r"[\d\s☞]+", t)):
                    satirlar.append((r, t))
        if not satirlar:
            continue
        ust = min(r.y0 for r, _ in satirlar) - 2
        alt = max(r.y1 for r, _ in satirlar) + 2
        for im in sayfa.get_image_info():  # satırların altındaki görseller de sayfa içeriğidir
            r = pymupdf.Rect(im["bbox"])
            if r.y1 < H * 0.93 and r.get_area() < 0.5 * W * H:
                alt = max(alt, r.y1 + 2)
        orta = W / 2
        adaylar = [r for r, t in satirlar if NO_BAS.match(t)]
        sol = min((r.x0 for r in adaylar if r.x0 < orta - 40), default=min(r.x0 for r, _ in satirlar))
        # Sağ sütun soru numarası tek başına bir satırdır ("6."); sağ yarıda başlayan "2. grup: …" gibi
        # metin satırları sütun kenarı sayılmaz (tek sütunlu sayfa yanlışlıkla ikiye bölünmesin).
        sag = min((r.x0 for r, t in satirlar if r.x0 >= orta - 40 and NO_BAS.match(t)
                   and (re.fullmatch(r"\d{1,2}\.", t) or r.x0 <= orta + 25)), default=None)
        sinir = (sag - 3) if sag is not None else W
        x_sol, x_sag = max(0, sol - 8), min(W, W - sol + 8)
        tam_satirlar = [r for r, _ in satirlar if r.x0 < sinir - 20 and r.x1 > sinir + 20]

        # Başlangıçlar: (y, sütun, [hedef no'lar], tür)
        baslar = []
        for r, t in sorted(satirlar, key=lambda o: (o[0].y0, o[0].x0)):
            st = "sag" if (sag is not None and r.x0 >= sinir - 2) else "sol"
            k = KOK.search(t)
            if k and k.start() < 6:
                baslar.append([r.y0, st, [int(x) for x in re.findall(r"\d+", k.group(1))], "kok", r])
                continue
            m = NO_BAS.match(t)
            kenar = sag if st == "sag" else sol
            if m and abs(r.x0 - kenar) <= 5:
                baslar.append([r.y0, st, [int(m.group(1))], "soru", r])
        # Okuma sırasıyla doğrula (sol sütun sonra sağ; tam genişlik bantları sırayı böler).
        def tam_mi(b):
            y0 = b[0]
            sonraki = min([x[0] for x in baslar if x[1] == b[1] and x[0] > y0] + [y0 + 60])
            # Aynı yükseklik aralığında sağ sütunda başka bir soru başlıyorsa soru tam genişlik olamaz.
            sagda = any(x[1] == "sag" and y0 - 8 <= x[0] < sonraki for x in baslar)
            return b[1] == "sol" and not sagda and any(y0 - 2 <= r.y0 < sonraki for r in tam_satirlar)
        for b in baslar:
            b[1] = "tam" if tam_mi(b) else b[1]
        sirali, kesit = [], []
        for b in sorted(baslar, key=lambda b: b[0]):
            if b[1] == "tam":
                sirali += sorted(kesit, key=lambda b: (b[1] == "sag", b[0])) + [b]
                kesit = []
            else:
                kesit.append(b)
        sirali += sorted(kesit, key=lambda b: (b[1] == "sag", b[0]))
        # Sayfadaki soru numaraları sıra düzeninden bağımsız kabul edilir (sütun ya da satır düzeni):
        # beklenen aralıktaki (son+1 … son+sayfadaki aday sayısı+1) her numara bir kez alınır.
        gecerli, alinan = [], set()
        sorular_ = [b for b in sirali if b[3] == "soru"]
        ust_sinir = min(son + len(sorular_) + 1, a.soru_sayisi)
        for b in sirali:
            if b[3] == "kok":
                gecerli.append(b)
                continue
            n = b[2][0]
            if son < n <= ust_sinir and n not in alinan:
                alinan.add(n)
                gecerli.append(b)
        if alinan:
            eksik_ = [n for n in range(son + 1, max(alinan)) if n not in alinan]
            if eksik_:
                uyarilar.append(f"s{no}: {eksik_} numaralı soru(lar) bu sayfada bulunamadı")
            son = max(alinan)
        # Sayfa başında numarasız içerik: önceki sorunun devamı.
        if hedef and gecerli and min(b[0] for b in gecerli) - ust > 30:
            ilk = min(b[0] for b in gecerli)
            for n in hedef:
                bolge.setdefault(n, []).append((no, pymupdf.Rect(x_sol, ust, x_sag, ilk - 2)))
        # Bölgeler
        for b in gecerli:
            y0, st = b[0], b[1]
            alt_sinir = [x[0] for x in gecerli if x[0] > y0 + 1 and (st == "tam" or x[1] in (st, "tam"))]
            alt_sinir += [r.y0 for r in tam_satirlar if r.y0 > y0 + 1] if st != "tam" else []
            y1 = min(alt_sinir + [alt]) - 2
            x0, x1 = {"sol": (x_sol, sinir - 4), "sag": (sinir - 4, x_sag), "tam": (x_sol, x_sag)}[st]
            r = pymupdf.Rect(x0, y0 - 3, x1, y1)
            for n in b[2]:
                bolge.setdefault(n, []).append((no, r))
            hedef = b[2] if b[3] == "soru" else hedef
        if gecerli:
            sorular_ = [b for b in gecerli if b[3] == "soru"]
            if sorular_:  # sonraki sayfanın başındaki numarasız içerik en büyük numaralı soruya aittir
                hedef = max(sorular_, key=lambda b: b[2][0])[2]
    for n, liste in sorted(bolge.items()):
        harita[f"{a.ders}-{n:02d}"] = [
            {"sayfa": s, "kutu": [round(r.x0 / doc[s - 1].rect.width, 4), round(r.y0 / doc[s - 1].rect.height, 4),
                                  round(r.x1 / doc[s - 1].rect.width, 4), round(r.y1 / doc[s - 1].rect.height, 4)]}
            for s, r in liste if r.height > 4]
    eksik = [n for n in range(1, a.soru_sayisi + 1) if n not in bolge]
    ortak.yaz(a.harita, harita)
    for u in uyarilar:
        print("  UYARI", u)
    print(f"{a.ders}: {len(bolge)} soru haritalandı" + (f"; EKSİK: {eksik}" if eksik else ""))


NO_BAS = re.compile(r"^(\d{1,2})\.(?:\s|$)")


def komut_pano(a):
    """Kırpımların küçük resimlerini tek görselde ızgara olarak dizer (hızlı göz kontrolü için)."""
    import glob
    dosyalar = sorted(glob.glob(os.path.join(a.klasor, f"{a.onek}*.png")))
    if not dosyalar:
        sys.exit("kırpım bulunamadı")
    sutun, hucre_g, hucre_y, baslik = a.sutun, 400, 520, 14
    satir = (len(dosyalar) + sutun - 1) // sutun
    doc = pymupdf.open()
    p = doc.new_page(width=sutun * hucre_g, height=satir * (hucre_y + baslik))
    for i, f in enumerate(dosyalar):
        x, y = (i % sutun) * hucre_g, (i // sutun) * (hucre_y + baslik)
        p.insert_text((x + 4, y + 11), os.path.basename(f)[:-4], fontsize=11, color=(0.8, 0, 0))
        p.insert_image(pymupdf.Rect(x + 2, y + baslik, x + hucre_g - 2, y + baslik + hucre_y - 2),
                       filename=f, keep_proportion=True)
        p.draw_rect(pymupdf.Rect(x + 1, y + baslik, x + hucre_g - 1, y + baslik + hucre_y - 1),
                    color=(0.6, 0.6, 0.6), width=0.5)
    p.get_pixmap(matrix=pymupdf.Matrix(a.olcek, a.olcek)).save(a.cikis)
    print(f"{len(dosyalar)} kırpım -> {a.cikis}")


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
    h = alt.add_parser("harita")
    h.add_argument("pdf")
    h.add_argument("bloklar")
    h.add_argument("harita")
    h.add_argument("--ders", required=True)
    h.add_argument("--sayfalar", required=True)
    h.add_argument("--soru-sayisi", type=int, required=True)
    h.add_argument("--ayrinti", action="store_true", help="blok bazında kararları yazdır")
    hm = alt.add_parser("harita-metin", help="metin katmanlı PDF için blok gerektirmeyen harita")
    hm.add_argument("pdf")
    hm.add_argument("harita")
    hm.add_argument("--ders", required=True)
    hm.add_argument("--sayfalar", required=True)
    hm.add_argument("--soru-sayisi", type=int, required=True)
    pn = alt.add_parser("pano", help="kırpımları tek görselde ızgara olarak göster")
    pn.add_argument("klasor")
    pn.add_argument("cikis")
    pn.add_argument("--onek", default="")
    pn.add_argument("--sutun", type=int, default=5)
    pn.add_argument("--olcek", type=float, default=1.0)
    a = ap.parse_args()
    {"bloklar": komut_bloklar, "kes": komut_kes, "harita": komut_harita, "pano": komut_pano, "harita-metin": komut_harita_metin}[a.komut](a)


if __name__ == "__main__":
    ortak.utf8()
    main()
