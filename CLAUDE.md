# TYMM Süreç Bileşeni Eşleştirme

## Amaç

Deneme kitapçıklarındaki (PDF, görseller içerir) her soruyu Türkiye Yüzyılı Maarif Modeli (TYMM)
öğretim programındaki **öğrenme çıktısı** (kod + metin) ve **süreç bileşenleri** (a, b, c, ç…) ile eşleştiren
bir Claude Code skill'i geliştirmek. **Yalnızca Claude Code'da (bu repoda) çalışır**; claude.ai'ye yüklenmez.

Skill, karar verirken referansın yanında **örnek bankasını** kullanır: yayınevi kazanım tablolarıyla
doğrulanmış soru görseli ↔ öğrenme çıktısı / süreç bileşeni çiftleri. Kullanıcı yeni denemeleri
PDF + yayınevi tablosu olarak verir; `tymm-ornek-ekle` skill'i bunları bankaya ekler.

## Repo yapısı

- `tymm_programmes/pdf_files/` — resmi program PDF'leri (kaynak ve PID listesi: `KAYNAK.md`). PDF'ler metin
tabanlı; `pdftotext -layout` ile temiz çıkıyor.
  - kök: TYMM ortaokul (Fen, Matematik, Türkçe, Sosyal Bilgiler, İngilizce 2–8, İnkılap Tarihi 8,
  Din Kültürü 4–8) + `ortak-metin.pdf`
  - `lise/`: TYMM lise (9–12) programları
  - `eski-program/ortaokul/`, `eski-program/lise/`: 2018 programları (8. ve 12. sınıfta hâlâ geçerli; LGS/YKS).
  Eski programlarda **süreç bileşeni yok**, yalnızca kazanım var (kod biçimi farklı, ör. `M.8.1.1.1.`).
- `tymm_programmes/taslak_plans/` — 2026-2027 taslak çerçeve yıllık planları (zip içinde xlsx).
- `.claude/skills/tymm-surec-eslestirme/` — etiketleme skill'i.
  - `SKILL.md` — iş akışı (frontmatter: `name`, `description`)
  - `referans/<ders>/<sınıf>.json` — çıktılar, süreç bileşenleri, plan haftaları (şema: `referans/README.md`)
  - `ornekler/<ders>/<sınıf>.json` — örnek bankası etiketleri (şema: `ornekler/README.md`);
  `ornekler/<ders>/gorsel/` — kırpılmış soru görselleri, **git dışında** (yayınevi içeriği)
  - `scripts/` — skill'in kullandığı betikler: `sayfa_goruntule.py`, `soru_kirp.py` (bloklar / harita-metin /
  kes / pano), `soru_metni.py` (soru başına metin), `kapsam.py` (aday çıktı listesi), `yayinevi_tablo.py`
  (xlsx → tablo.json), `ornek_ekle.py`, `ornek_bul.py`, `degerlendir.py`, `ortak.py`
- `.claude/skills/tymm-ornek-ekle/` — PDF + yayınevi tablosunu bankaya ekleme skill'i (betikleri yukarıdakilerdir).
- `data/` — deneme verisi; **git dışında**, içerikler salt okunur (yayınevi içeriği, **dağıtılmaz**).
Ayrıntı `data/README.md`. İki üst klasör:
  - `data/kullanilacak/` — her deneme bir kazanım tablosu (`dt2_*.xlsx|.xls`) + kitapçık (`dt3_*.pdf`) çifti.
  Okulizyon setleri `<set>/<yayınevi>/<yıl>/<sınav no>_<ad>/` düzeninde; Okulizyon hesabı sahibinin izniyle
  indirildi (araç ve arşiv listeleri: `tmp/okulizyon/`).
    - `5-7_tymm/` — 245 (5: 152, 6: 76, 7: 17); TYMM, süreç bileşeni dahil. İşleyen Zeka 2026–27 Gelişim
    İzleme 1 (5/6/7) zaten bankada.
    - `8_lgs/` — 153; **eski (2018) programa** göre, yalnızca kazanım (kullanıcı kararı 2026-11-17). 5–7 ile
    karıştırılmaz.
    - `9-11_tymm/` — 218; TYMM. 10'u 2026–27 "MAARİF" serisi (sınıf düzeyi incelenmedi).
    - `yks/` — 349 TYT/AYT/YDT/MSÜ (2025–26, 2026–27); **eski (2018) lise programına** göre, yalnızca kazanım
    (kullanıcı kararı 2026-11-17).
    - `kullanici/` — kullanıcının verdiği dosyalar (`pdf_dosyalari/`, `excel_dosyalari/`): Yargı Sıfır Tolerans
    Süreç İzleme-2 ve İşleyen Zeka Gelişim İzleme 1 (5–8). 5–7 olanlar bankada; **Yargı 5 sabit test seti**.
  - `data/kullanilmayacak/` — `iskarta/<set>/` (eksik/uygunsuz çiftler, nedenleri `NEDEN.txt`) ve `kullanici/`
  (kitapçığı olmayan Bilgi Sarmal Maarif ve Hız ve Renk TYT; PDF'leri yalnızca cevap anahtarı).
- `scripts/` — yalnızca referans üretimi betikleri.

## Kaynak dosya kuralları

- `tymm_programmes/` altındaki PDF ve zip dosyaları **salt okunurdur**; değiştirme, taşıma, silme.
- Zip'leri ve PDF metin çıktılarını yalnızca `tmp/` altına çıkar (`.gitignore`'da tanımlı, commit'lenmez).
- Bazı dosya adlarında boşluk/parantez var (`... (2).pdf`); komutlarda yolları tırnakla.
- Türkçe arşivindeki `2026-2027 Türkçe 8 Hecce Yayınları Çerçeve Yıllık Plan.xlsx` bir yayınevi
planıdır, **kullanılmaz**. Yalnızca `TÜRKÇE (5-8. SINIFLAR) TASLAK ÇERÇEVE YILLIK PLAN+++.xlsx` esas alınır.
- Kaynak önceliği: çıktı kodu/metni ve süreç bileşenleri → program PDF'i; hafta dağılımı → taslak plan.
Çelişki varsa PDF esas alınır ve kullanıcıya bildirilir.

## Geliştirme ortamı (Windows)

- Python: proje sanal ortamı `.venv\Scripts\python.exe` (Python 3.12, `openpyxl` kurulu). `.venv` commit'lenmez.
Sistemdeki `python` komutu Microsoft Store kısayoludur; kullanma.
- `pdftotext`: Git Bash içinde mevcut (`/mingw64/bin/pdftotext`). Türkçe karakterler için mutlaka
`-enc UTF-8` ver; aksi halde ı/ş/ğ/İ bozulur.
- `pdftoppm` yok; Read aracı PDF sayfalarını görüntüleyemez. Sayfayı görsel doğrulamak için
`.venv` içindeki PyMuPDF ile `tmp/sayfa/` altına PNG üret ve onu oku.
- `.venv` paketleri: `openpyxl`, `pymupdf`, `numpy`. Skill betiklerini `.venv/Scripts/python.exe -I` ile çalıştır.
- Referans üretimi (hepsi için `bash scripts/referans_hepsi.sh`):
  - `scripts/referans_cikar.py <ders> <sınıf>` — Matematik, Fen, Sosyal, İngilizce (PDF metni → JSON)
  - `scripts/referans_turkce.py <sınıf>` — Türkçe (tema sayfaları + PyMuPDF ile 9. Tablo)
  - `scripts/plan_haftalari.py <ders> <sınıf>` — taslak plan haftaları → JSON
  - `scripts/referans_bol.py <ders> <sınıf>` — Türkçe/İngilizce ana dosya + parça dosyalarına böler
  - Betikler çapraz kontrol uyarıları yazdırır; yeni uyarı çıkarsa nedenini bulmadan geçme.
- Bu `scripts/` araçları yalnızca referans verisini hazırlamak içindir; skill'in kullanımında gerekmez.

## Alınan kararlar

- Çıktı kodları ve süreç bileşeni metinleri **yalnızca** referans dosyalarından alınır; ezberden kod uydurulmaz.
- Bir soru birden fazla süreç bileşenine eşlenebilir.
- Her eşleşme için güven düzeyi + kısa gerekçe verilir; emin olunmayanlar "kontrol edilmeli" olarak işaretlenir.
- Yıllık plan, denemenin tarihine göre kapsamı daraltmak için kullanılır.
- **Onay kaynağı yayınevi tablosudur.** Tablodaki küçük hatalar tolere edilir, etiket değiştirilmez.
Tabloda eksik olan çıktı/bileşeni Claude tamamlar ve `etiket_kaynagi` ile işaretler
(`yayinevi` / `yayinevi+claude` / `claude`).
- Örnek bankası hem etiketleme kanıtı hem test setidir (eski `tests/altin` buraya taşındı). Soru
görselleri git'e girmez; yalnızca etiket JSON'ları commit'lenir.
- Aynı denemenin A/B kitapçıklarından yalnızca biri bankaya eklenir.
- Yeni deneme bankaya eklenmeden önce tabloya bakılmadan etiketlenir ve ölçülür (önce test, sonra örnek).
- Ayrım notları `referans/<ders>/<sınıf>-notlar.md` ya da `notlar-genel.md` içine yazılır ve **yalnızca program
metnine dayanır**. Kullanıcı kararı (2026-11-17): yayınevi alışkanlıkları (programla açıklanamayan, yayınevine
özgü çıktı/bileşen tercihleri) görmezden gelinir; etiketleme kararı program metnine göre verilir.
- MEB örnek soruları şu an yok.

## Test iş akışı (Claude Code'da)

1. Kullanıcı PDF + yayınevi tablosu verir; dosyaları `tmp/` altına koy.
2. Bankada o ders/sınıf için başka kaynak varsa: `tymm-surec-eslestirme` ile tabloya bakmadan etiketle,

   `tahmin.json` kaydet.
3. `tymm-ornek-ekle` ile bankaya ekle (tablo → şablon, kırpma, tamamlama, `ornek_ekle.py`).
4. `degerlendir.py tahmin.json --kaynak <id>` ile ölç; hatalardan çıkan ayrım kurallarını

   `<sınıf>-notlar.md`'ye ve ilgili örneğin `ipucu` alanına yaz.

- Kitapçık bankada varken yeniden etiketlenecekse `ornek_bul.py --haric <id>` kullanılır (sızıntı olmasın).
- **8. sınıf ayrı ele alınır.** İlk aşama 5–7. sınıflardır. 8. sınıf (LGS denemeleri, İnkılap Tarihi dahil)
ayrı bir aşamada yapılır; hangi programa göre eşleneceği o aşamada netleşir. 8. sınıf referansları
5–7 ile karıştırılmaz.

## Referans çıkarımında dikkat

- Program PDF'lerinde blok yapısı: "ÖĞRENME ÇIKTILARI VE SÜREÇ BİLEŞENLERİ" → `MAT.5.1.2. <çıktı metni>`
ardından `a) … b) … c) ç) d) e) f) g) ğ) h) ı) i) …` (Türkçe alfabe sırası). Satır sonu tirelemelerini birleştir.
- Kod formatları: `MAT.5.1.1.`, `FB.5.1.1.`, `SB.5.1.1.`, `ENG.5.1.L1.` (beceri harfi L/R/S/W/V/G/P),
Türkçe `T.D.5.3.` / `T.O.` / `T.K.` / `T.Y.` (Dinleme/İzleme, Okuma, Konuşma, Yazma).
- Tema başlıkları: "N. TEMA:", "N. ÜNİTE:" (Fen), "N. ÖĞRENME ALANI:" (Sosyal), "THEME N:" (İngilizce).
- Türkçe'de süreç bileşenleri tema sayfalarında değil "9. Tablo"dadır (yan çevrilmiş sayfalar, 5–8.
sınıf kodları yan yana). Sol sütun satırları PyMuPDF'te y1 ≈ 795.6'da biter. Aynı başlık farklı
beceri alanlarında olabilir; sayfanın "ALAN BECERİSİ" başlığıyla ayırt edilir.
- PDF'lerde kod yazım hataları var (`ENG5.7.L1.`, `ENG.5.8.R 4.`, kodla metin arasında boşluk yok);
bazı satırlarda pdftotext boşlukları kaybediyor (FB.5.3.1.) → PyMuPDF ile onarılıyor.
- Kaynakta eksikler `kaynak_notlari`'na yazılır, uydurulmaz: ör. ENG.7.5.W7. listede yok; bazı Türkçe
çıktılarda (Akıcı okuyabilme vb.) süreç bileşeni verilmemiş.
- **2026-2027 taslak planında 7. sınıf İngilizce eski programla** (E7.x kodları) hazırlanmış. Kullanıcı
kararı (2026-11-17): 7. sınıf İngilizce de **TYMM'ye (ENG.7) göre** eşlenir; plan haftaları kullanılamaz.
- Doğrulama: Matematik/Fen/Sosyal/Türkçe için tema bazında çıktı sayıları ve ders saatleri PDF'teki
özet tablolarla birebir tutuyor (5–7). Plan haftaları: tüm kodlar planda bulundu (İngilizce 7 hariç).

## Açık sorular

1. 8. sınıf: karar verildi (2026-11-17) — eski (2018) programa göre, yalnızca kazanım. Eski program referans
   çıkarıcısı henüz yazılmadı.
2. Lise / YKS: kapsama alındı (2026-11-17): 9–11 TYMM'ye, YKS eski programa göre. TYMM lisede 9 (2024–25),
   10 (2025–26), 11 (2026–27) sınıflarda yürürlükte. Referansları henüz üretilmedi; sıralaması (8. sınıf,
   lise, YKS) netleşmedi.

## Sonraki adımlar

Bankada (2026-11-17): eksen-5 (yalnız Mat), İşleyen Zeka Gelişim İzleme 1 (5, 6, 7), Yargı Süreç İzleme 2
(6, 7). Ölçüm günlüğü: `tmp/ornek/OLCUMLER.md` (git dışında). Bekleyenler:
1. Yargı 5 (`data/kullanilacak/kullanici/`): sabit test seti olarak ayrıldı; bankaya eklenmeden ölçülecek. Bu oturumda tablosu
   görüldüğü için ölçüm yeni bir oturumda yapılmalı.
2. eksen-5-sd1-a'nın diğer dersleri (`tmp/sayısal.pdf`, `tmp/sosyal.pdf`, tablo.json hazır).
3. Yargı kırpımlarından bazıları eksik (ör. yargi-6 fen-01/02); pano ile gözden geçirip haritayı elle düzelt.
4. Yayınevi alışkanlıkları görmezden gelinir. Ölçümde yayınevi tercihinden kaynaklanan farklar "kendi hatası"
   sayılmaz; hata analizi `tmp/ornek/OLCUMLER.md`'de. Yeni karar yöntemi (SKILL.md 6. adım) yeni bir denemeyle ölçülmeli.
5. İngilizce: yayınevi etiketleri tahmin edilemiyor / eski program; ölçümden ayrı tutulmalı.
6. Açık soruları netleştir (8. sınıf, lise/YKS). Din Kültürü programları (TYMM 4–8 ve 9–12, 2018 4–8 ve 9–12)
   artık repoda.
7. `data/kullanilacak/5-7_tymm/` (245 sınav) bankaya eklenmeyi bekliyor. 12'sinin tablosu eski `.xls` biçiminde (GO, MUBA);
   `yayinevi_tablo.py`'nin bunu okuyup okumadığı kontrol edilmeli. Yargı arşivde yok (Yargı 5 sabit test seti etkilenmez).
8. **Toplu soru çıkarma** (devam eden iş, ayrıntı: `tmp/pilot/README.md`). Amaç: ~106 bin sorunun (tablolardan
   sayıldı; ~95 bini dijital kitapçıkta) soru başına kırpım + JSON kaydı (etiket + meta veri) ile bankaya/teste
   alınması. Durum (2026-11-18):
   - Kitapçıkların %89'u dijital (metin katmanlı), %11'i görüntü (çoğu Okyanus, GO). Sınıflama: `tmp/pilot/dijital.json`.
   - Dijital yöntem prototipi (`tmp/pilot/kirp_dijital.py` + `filigran.py`): 9 dijital pilot sınavda soru sayısı
     tutma %84, panolardan temiz kırpım ~%85–90. Zayıf: Kafa Dengi, Klasman; iç içe gömülü filigran bazı sayfalarda kalıyor.
   - Kullanıcı tercihi: **PNG üzerinden öğrenen bir soru tespit modeli** (YOLO, RTX 5090 mevcut). Dijital yöntem
     modele etiket üretir. PyTorch (CUDA 12.8) + Ultralytics kurulumu için **kullanıcı onayı bekleniyor**.
   - Kullanıcı AV 7467 kontrol görsellerini (`tmp/pilot/7467/kontrol/`) inceliyor; geri bildirimi bekleniyor.
9. `tmp/okulizyon_cerez.txt` (Okulizyon hesap sahibinin oturum çerezi, kişisel veri) artık gerekmiyor; silinmeli.
