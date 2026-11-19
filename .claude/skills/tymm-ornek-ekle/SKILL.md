---
name: tymm-ornek-ekle
description: Yayınevinin kazanım tablosu verilmiş bir deneme kitapçığını (PDF + tablo) TYMM örnek bankasına ekler - tabloyu standart şablona çevirir, eksik öğrenme çıktısı/süreç bileşenlerini tamamlar, soruları tek tek kırpar ve doğrulayıp bankaya yazar. Kullanıcı "örnek ekle", "bu denemeyi bankaya ekle", "kazanım tablosu/cevap anahtarı burada" dediğinde veya PDF ile birlikte yayınevi tablosu verdiğinde kullan.
---

# TYMM Örnek Bankasına Ekleme

Girdi: deneme kitapçığı PDF'i (bir ya da birkaç dosya) + yayınevinin kazanım tablosu (xlsx ya da
başka biçim). Çıktı: `tymm-surec-eslestirme/ornekler/<ders>/<sınıf>.json` içinde doğrulanmış
soru ↔ etiket kayıtları ve git dışında tutulan soru görselleri.

**Onay kaynağı yayınevi tablosudur.** Tablodaki küçük hatalar (yazım farkı, eksik kelime, çıktı ile
bileşen metninin karışması) tolere edilir; tablo etiketi değiştirilmez. Yalnızca tabloda olmayan
bilgi (eksik çıktı kodu ya da bileşen) Claude tarafından tamamlanır ve öyle işaretlenir.

```bash
PY=".venv/Scripts/python.exe -I"; S=.claude/skills/tymm-surec-eslestirme/scripts
```
Bütün ara dosyalar `tmp/ornek/<kaynak-id>/` altında (git dışında) tutulur.

## 0. Kaynak kimliği
`<yayınevi>-<sınıf>-<deneme kısaltması>-<kitapçık>` (küçük harf, ASCII, tire), ör. `eksen-5-sd1-a`.
Yayınevi, deneme adı ya da tarih belirsizse kullanıcıya sor. Aynı denemenin farklı kitapçıkları
(A/B) aynı soruları içerir; **yalnızca bir kitapçığı** ekle (tekrarlı örnek bankayı çarpıtır).

## 1. Önce ölç (önerilir)
O ders/sınıf için bankada başka kaynak varsa, eklemeden önce kitapçığı `tymm-surec-eslestirme`
ile **tabloya bakmadan** etiketle ve `tmp/ornek/<kaynak-id>/tahmin.json` olarak kaydet.
Bankaya ekledikten sonra (6. adım) ölç. Her yeni deneme böylece önce test, sonra örnek olur.

## 2. Tabloyu şablona çevir
```bash
$PY $S/yayinevi_tablo.py <tablo.xlsx> --sinif 5 --kitapcik A --kaynak-id <id> \
    --deneme "<deneme adı>" --yayinevi "<yayınevi>" [--tarih YYYY-AA-GG] -o tmp/ornek/<id>/tablo.json
```
Betik "Ders", "Kazanım…" ve kitapçık harfi sütunlarını tanır; her yayınevi metnini referansla eşler:

| `duzey` | Anlamı | Yapılacak |
|---|---|---|
| `bilesen` | Metin bir bileşenle eşleşti: çıktı + bileşen tablodan | `etiket_kaynagi: "yayinevi"` (betik doldurur) |
| `cikti` | Metin çıktının kendisi: bileşen yok | Bileşeni soruya bakarak seç → `"yayinevi+claude"` |
| `yok` / `belirsiz` | Serbest etiket, eski program, başka sınıf… | Çıktı + bileşeni seç → `"claude"` |
| `referans yok` | Din Kültürü vb. | Atla |

`yakin_ifade` notu küçük yazım farkıyla kabul edilen eşleşmeleri gösterir; anlamın gerçekten aynı
olduğunu göz ucuyla kontrol et.

Tablo bu biçimde değilse (PDF tablo, görsel, farklı sütunlar, kod içeren tablo) Claude aynı
şablonu elle üretir: şema `tymm-surec-eslestirme/ornekler/README.md`. Metin eşleme için
`ortak.metin_esle` kullanılabilir.

Kontrol: tablodaki ders başına soru sayısı kitapçıktakiyle aynı mı? Kitapçık harfi doğru sütun mu?
Soru no sütunu yoksa (ör. Yargı tabloları) numara ders içindeki satır sırasından verilir. **Satır kayması**
olabilir (İşleyen Zeka 6 Fen 2-5): kırptıktan sonra her satırın metnini soruyla karşılaştır; kaymışsa satırları
içeriğe göre hizala (etiketi değiştirmeden) ve `not` yaz.

## 3. Soruları kırp
**Metin katmanlı PDF (önce bunu dene):** sayfa/blok önizlemesi gerekmez. Her ders için:
```bash
$PY $S/soru_kirp.py harita-metin <kitapçık.pdf> tmp/ornek/<id>/harita-<pdf-adı>.json     --ders <ders> --sayfalar <ilk-son> --soru-sayisi <n>
$PY $S/soru_kirp.py kes <kitapçık.pdf> - tmp/ornek/<id>/harita-<pdf-adı>.json tmp/ornek/<id>/soru
$PY $S/soru_kirp.py pano tmp/ornek/<id>/soru tmp/ornek/<id>/pano-<ders>.png --onek <ders>   # tek görselde kontrol
$PY $S/soru_metni.py <kitapçık.pdf> tmp/ornek/<id>/harita-<pdf-adı>.json --onek <ders>       # soru metinleri
```
Numaralar sütun ya da satır düzeninde olabilir; "N ve M. soruları…" / "Answer the questions …" kökleri
ilgili sorulara eklenir; eğik filigran ve "6. Sınıf" sayfa başlığı ayıklanır. "EKSİK" uyarısı veren ya da
panoda kesik görünen soruyu haritada elle düzelt (`{"sayfa", "kutu"}`).

**Taranmış PDF:** her PDF için ayrı blok klasörü:
```bash
$PY $S/soru_kirp.py bloklar <kitapçık.pdf> tmp/ornek/<id>/<pdf-adı> [--sayfalar 2-8]
```
`<pdf-adı>/onizleme/sNN.png` dosyalarını oku: her blokta kırmızı kutu ve sol üstünde numara var.
Sonra `tmp/ornek/<id>/harita-<pdf-adı>.json` yaz. Anahtar `<ders>-<no:02d>`, değer blok kimlikleri:
```json
{"matematik-03": ["03.2", "03.3", "03.4", "03.5", "03.6"],
 "matematik-04": ["03.2", "03.3", "03.4", "03.7", "03.8"]}
```
- Soruya ait **her** bloğu listele: numara, kök, görseller, seçenekler. Sayfa başlığı, sayfa
  numarası ve "Diğer sayfaya geçiniz" bloklarını alma.
- Ortak yönerge/kök/görseli ("3 ve 4. soruları …") ilgili tüm soruların listesine yaz.
- Araç yan yana ve ardışık blokları, araya başka blok girmiyorsa tek dikdörtgende birleştirir;
  sütun değiştiren parçaları alt alta dizer. Bölme yetersizse elle bölge ver:
  `{"sayfa": 5, "kutu": [x0, y0, x1, y1]}` (0–1 oranları).
```bash
$PY $S/soru_kirp.py kes <kitapçık.pdf> tmp/ornek/<id>/<pdf-adı>/bloklar.json \
    tmp/ornek/<id>/harita-<pdf-adı>.json tmp/ornek/<id>/soru
```
Her kırpımı aç ve kontrol et: soru numarası, kök, tüm seçenekler ve gereken ortak içerik var mı;
başka sorudan parça girmiş mi? Sorunluysa haritayı düzelt ve yeniden kes.

## 4. Satırları tamamla
`tablo.json`'daki her satır için soruyu (kırpımı) okuyup şu alanları doldur:

- `ozet` (**her satır**): sorunun ne istediğini tek cümleyle anlatan, kimliği belli eden özet
  (ör. "Cetvelle ölçülen uzunluğun sembolle gösterimi seçenekler arasından seçiliyor.").
  Etiketi tekrar etme; görev türünü ve içeriği yaz.
- `duzey: cikti` → `bilesenler` için o çıktının bileşenlerinden birini seç;
  `etiket_kaynagi: "yayinevi+claude"`.
- `duzey: yok/belirsiz` → yayınevi metnini ipucu kabul ederek (eski program ifadesi, konu adı) çıktı ve
  bileşeni seç; `etiket_kaynagi: "claude"`. Emin değilsen `not` alanına yaz.
- `ipucu` (isteğe bağlı): etiket kolay karıştırılabilecekse ayırt edici kural (ör. "paralellik/diklik
  ifadesi → MAT.5.3.2 b; MAT.5.3.4 yalnızca oluşan açılar sorulunca"). Etiketleme sırasında
  `ornek_bul.py` bu ipuçlarını gösterir; en değerli alan budur.
- `duzey: bilesen` satırının etiketi soruyla **açıkça** uyuşmuyorsa (başka konu) etiketi değiştirme;
  `not` alanına yaz ve kullanıcıya bildir. Küçük uyumsuzlukları tolere et.

Tutarlılık için bankadaki mevcut örneklere bak: `$PY $S/ornek_bul.py <ders> <sınıf> <kodlar>`.

## 5. Kullanıcıya göster, sonra ekle
Kullanıcıya kısa bir özet ver:
- Claude'un tamamladığı satırlar (`yayinevi+claude`, `claude`): no, yayınevi metni, seçilen etiket, gerekçe.
- `yakin_ifade` ile kabul edilen eşleşmeler ve `not` düşülen satırlar.
- Atlanan dersler (referans yok).

Kullanıcı itiraz etmezse:
```bash
$PY $S/ornek_ekle.py tmp/ornek/<id>/tablo.json tmp/ornek/<id>/soru --kuru   # yalnızca denetim
$PY $S/ornek_ekle.py tmp/ornek/<id>/tablo.json tmp/ornek/<id>/soru
```
Betik çıktı kodunu ve bileşen harflerini referansla denetler; eksik satırları eklemez. Aynı kaynak
tekrar eklenirse eski kayıtların yerine geçer.

## 6. Ölç ve kuralları güncelle
1. adımda tahmin ürettiysen:
```bash
$PY $S/degerlendir.py tmp/ornek/<id>/tahmin.json --kaynak <id>
```
Ölçüm: `yayinevi` satırlarında çıktı + bileşen, `yayinevi+claude` satırlarında yalnızca çıktı ölçülür;
`claude` satırları ölçülmez. Tahminde tablo satırını önceden gördüğün soruyu `"sizinti": true` ile işaretle.
Sonucu `tmp/ornek/OLCUMLER.md` günlüğüne ekle.
Yanlış etiketlenen her soruyu sınıflandır: (1) **kendi hatası** — program metnine göre yayınevi etiketi
daha doğru (soruyu tam okumama, konu kelimesine takılma, komşu çıktıyı elememe, bileşen fiilini
eşleştirmeme); (2) **yayınevi tercihi** — program metniyle açıklanamayan ya da iki çıktının da savunulabildiği
durum. Yalnızca (1)'den çıkan, program metnine dayanan ayrımları `referans/<ders>/<sınıf>-notlar.md`
(ya da `notlar-genel.md`) dosyasına ve ilgili örneğin `ipucu` alanına yaz; yayınevi alışkanlıklarını kural yapma. Doğruluğu
kullanıcıya ders bazında bildir (yayınevi etiketli / Claude tamamlamış ayrı).
