# TYMM Süreç Bileşeni Eşleştirme

## Amaç
Deneme kitapçıklarındaki (PDF, görseller içerir) her soruyu Türkiye Yüzyılı Maarif Modeli (TYMM)
öğretim programındaki **öğrenme çıktısı** (kod + metin) ve **süreç bileşenleri** (a, b, c, ç…) ile eşleştiren
bir Claude Code skill'i geliştirmek.

## Repo yapısı
- `tymm_programmes/pdf_files/` — resmi TYMM program PDF'leri (Fen, Matematik, Türkçe, Sosyal Bilgiler,
  İngilizce 2–8, İnkılap Tarihi 8). PDF'ler metin tabanlı; `pdftotext -layout` ile temiz çıkıyor.
- `tymm_programmes/taslak_plans/` — 2026-2027 taslak çerçeve yıllık planları (zip içinde xlsx).
- `skill/tymm-surec-eslestirme/` — skill'in kendisi. Bu klasör zip'lenip claude.ai'ye yüklenir;
  Claude Code'da da aynı klasör kullanılır.
  - `SKILL.md` — iş akışı (frontmatter: `name`, `description`)
  - `referans/<ders>/<sınıf>.json` — çıktılar, süreç bileşenleri, plan haftaları (şema: `referans/README.md`)

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
- `.venv` paketleri: `openpyxl`, `pymupdf`.
- Referans üretimi (hepsi için `bash scripts/referans_hepsi.sh`):
  - `scripts/referans_cikar.py <ders> <sınıf>` — Matematik, Fen, Sosyal, İngilizce (PDF metni → JSON)
  - `scripts/referans_turkce.py <sınıf>` — Türkçe (tema sayfaları + PyMuPDF ile 9. Tablo)
  - `scripts/plan_haftalari.py <ders> <sınıf>` — taslak plan haftaları → JSON
  - `scripts/referans_bol.py <ders> <sınıf>` — Türkçe/İngilizce ana dosya + parça dosyalarına böler
  - Betikler çapraz kontrol uyarıları yazdırır; yeni uyarı çıkarsa nedenini bulmadan geçme.
- Bu araçlar yalnızca referans verisini hazırlamak içindir; skill'in kullanımında gerekmez.

## Alınan kararlar
- Çıktı kodları ve süreç bileşeni metinleri **yalnızca** referans dosyalarından alınır; ezberden kod uydurulmaz.
- Bir soru birden fazla süreç bileşenine eşlenebilir.
- Her eşleşme için güven düzeyi + kısa gerekçe verilir; emin olunmayanlar "kontrol edilmeli" olarak işaretlenir.
- Yıllık plan, denemenin tarihine göre kapsamı daraltmak için kullanılır.
- Yayınevinin kazanım tablosu/cevap anahtarı, skill'in ilk çıkarımından sonra kullanıcı tarafından
  doğrulama için sağlanacak.
- Altın set: `tests/altin/<ders>-<sınıf>.json` — kullanıcının doğruladığı eşleştirmeler (yalnızca soru
  özeti; soru görselleri commit'lenmez). Skill kuralı değişince bu sete karşı yeniden test et.
- Doğrulanmış ayrım kuralları `referans/<ders>/<sınıf>-notlar.md` içine yazılır.
- MEB örnek soruları şu an yok.

## Test iş akışı (Claude Code'da)
1. Kitapçığı `tmp/` altına koy; `scripts/sayfa_goruntule.py <pdf> tmp/test/<ad> --sutun` ile sayfaları
   PNG'ye çevir ve oku.
2. `SKILL.md` iş akışını uygula; tabloyu kullanıcıya ver, makinece okunur hâlini
   `tmp/test/<ad>/tahmin.json` olarak kaydet.
3. Kullanıcı doğruladıktan sonra doğru etiketleri `tests/altin/<ders>-<sınıf>.json`'a ekle; hatalardan
   çıkan ayrım kurallarını `<sınıf>-notlar.md`'ye yaz.
4. `scripts/degerlendir.py tahmin.json tests/altin/<ders>-<sınıf>.json` ile doğruluğu ölç.
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
- **2026-2027 taslak planında 7. sınıf İngilizce eski programla** (E7.x kodları) hazırlanmış; TYMM ENG.7
  referansı var ama kullanmadan önce kullanıcıya sorulmalı.
- Doğrulama: Matematik/Fen/Sosyal/Türkçe için tema bazında çıktı sayıları ve ders saatleri PDF'teki
  özet tablolarla birebir tutuyor (5–7). Plan haftaları: tüm kodlar planda bulundu (İngilizce 7 hariç).

## Açık sorular
1. 8. sınıf aşaması: 2026-2027'de 4, 8 ve 12. sınıflarda hâlâ eski program uygulanıyor. 8. sınıf
   denemeleri TYMM'ye mi, eski programa mı göre eşlenecek? (5–7 tamamlandıktan sonra netleştirilecek.)
2. Din Kültürü ve Ahlak Bilgisi programı repoda yok; LGS denemeleri için gerekirse eklenmeli.

## Sonraki adımlar
1. Açık soruları netleştir.
2. Her ders/sınıf için referans JSON'larını çıkar; birkaç çıktıyı PDF ile karşılaştırarak doğrula.
3. SKILL.md iş akışını yaz.
4. İlk deneme kitapçığıyla test et; kullanıcı yayınevi kazanım tablosuyla karşılaştırsın, kuralları güncelle.