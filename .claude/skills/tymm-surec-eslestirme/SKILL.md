---
name: tymm-surec-eslestirme
description: Deneme/test kitapçığı PDF sayfalarındaki soruları Türkiye Yüzyılı Maarif Modeli (TYMM) öğretim programındaki öğrenme çıktıları ve süreç bileşenleriyle etiketler; doğrulanmış soru örneklerinden (örnek bankası) yararlanır. Kullanıcı bir deneme, test, sınav, süreç değerlendirme ya da soru kitapçığı PDF'i verip soruların hangi öğrenme çıktısına, kazanıma veya süreç bileşenine ait olduğunu sorduğunda; "soru-kazanım eşleştirmesi", "süreç bileşeni analizi", "TYMM eşleştirme" istediğinde kullan. Dersler - Türkçe, Matematik, Fen Bilimleri, Sosyal Bilgiler, İngilizce (5-7. sınıf).
---

# TYMM Süreç Bileşeni Eşleştirme

Verilen PDF sayfalarındaki her soruyu TYMM programındaki **öğrenme çıktısı** (kod + metin) ve
**süreç bileşeni** (a, b, c, ç, …) ile etiketler. Karar verirken iki kaynağa dayanır:

1. **Referans** (`referans/`): programdaki çıktı ve bileşenlerin kendisi. Kod ve metin yalnızca buradan alınır.
2. **Örnek bankası** (`ornekler/`): yayınevi tablosuyla doğrulanmış soru görseli ↔ etiket çiftleri.
   Benzer sorunun nasıl etiketlendiğini gösterir; özellikle aynı çıktının bileşenleri arasında
   seçim yaparken kullanılır. Ekleme iş akışı: `tymm-ornek-ekle` skill'i.

Bu skill yalnızca bu repoda, Claude Code içinde çalışır. Komutlar repo kökünden çalıştırılır:

```bash
PY=".venv/Scripts/python.exe -I"; S=.claude/skills/tymm-surec-eslestirme/scripts
```

## Temel kurallar

- Öğrenme çıktısı kodlarını ve süreç bileşeni metinlerini **yalnızca** referans dosyalarından al.
  Ezberden kod veya metin yazma. Örnekler de kod uydurmaya gerekçe olamaz.
- Referans dosyalarındaki `kaynak_notlari`'na uy (ör. bazı Türkçe çıktılarda programda bileşen
  verilmemiştir; o zaman yalnızca çıktıyı yaz).
- Referansı olmayan dersler (Din Kültürü, 8. sınıf, İnkılap Tarihi): soruları "referans yok" diye
  listele, eşleştirme yapma.
- TYMM terimlerini kullan ("öğrenme çıktısı", "süreç bileşeni"); kullanıcı "kazanım" derse anla.
- Kitapçıkta yayınevinin kazanım tablosu/cevap anahtarı varsa eşleştirmeyi **önce ona bakmadan** yap.

## Dosyalar

| Ne | Nerede |
|---|---|
| Çıktılar + bileşenler (Mat, Fen, Sosyal) | `referans/<ders>/<sınıf>.json` → `temalar[].ciktilar[]` |
| Türkçe | ana dosya `ciktilar[]`; bileşenler `bilesen_dosyasi` → `<sınıf>/okuma.json` vb. |
| İngilizce | ana dosya `temalar[]`; bileşenler `bilesen_dosyasi` → `<sınıf>/tema-N.json` |
| Ayrım notları (program metnine dayalı) | `referans/<ders>/<sınıf>-notlar.md` ya da `referans/<ders>/notlar-genel.md` |
| Örnek bankası | `ornekler/<ders>/<sınıf>.json` (etiketler) + `ornekler/<ders>/gorsel/` (git dışında) |

Ders klasörleri: `turkce`, `matematik`, `fen-bilimleri`, `sosyal-bilgiler`, `ingilizce`.

## İş akışı

### 1. Kitapçığı tanı
Sınıf, kitapçık türü (A, B …), sınav adı, tarih, dersler. Çok dersli kitapçıkta **her derste soru
numaraları 1'den başlar**; soruları her zaman "ders + soru no" ile an. Anlaşılmıyorsa kullanıcıya sor.

### 2. Soruları oku
```bash
$PY $S/sayfa_goruntule.py <kitapçık.pdf> tmp/test/<ad> --sutun
```
Sayfaları (iki sütunluysa yarıları) Read ile oku. PDF'ler çoğunlukla taranmıştır; şekil, grafik,
tablo ve metinleri görsel olarak oku. Ortak kök/görsel ("3 ve 4. soruları … göre") her iki soruya da
aittir. Kapaktaki soru sayısıyla bulunan sayı farklıysa belirt.

**Metin katmanlı PDF'lerde** (çoğu yeni deneme) soruları sütun sırası karışmadan okumak için önce
haritala, sonra her sorunun metnini kendi bölgesinden çıkar; şekil/grafik gerekiyorsa kırpımı aç:
```bash
$PY $S/soru_kirp.py harita-metin <kitapçık.pdf> tmp/test/<ad>/harita.json --ders matematik --sayfalar 18-24 --soru-sayisi 15
$PY $S/soru_metni.py <kitapçık.pdf> tmp/test/<ad>/harita.json --onek matematik
$PY $S/soru_kirp.py kes <kitapçık.pdf> - tmp/test/<ad>/harita.json tmp/test/<ad>/soru   # gerekirse görseller
```
Taranmış PDF'de `soru_kirp.py bloklar` akışı kullanılır (`tymm-ornek-ekle` 3. adım).

### 3. Referansı yükle, kapsamı daralt
Her ders için aday çıktıları kısa listeyle gör (`$PY $S/kapsam.py <ders> <sınıf> [--hafta N]`); varsa
`<sınıf>-notlar.md` / `notlar-genel.md`'yi de oku (komşu çıktıların program metnine göre ayrımı). Tarih verildiyse
`plan.haftalar` ile haftayı bul; `plan_haftalari` o haftaya kadar olan çıktıları öncelikli aday say.
Tarih yoksa sınav adından tahmin et ("Süreç Değerlendirme – 1" → yılın ilk haftaları) ve varsayımı
raporda belirt.

### 4. Aday çıktıları belirle
Her soru için 1–3 aday öğrenme çıktısı seç (konu + sorunun istediği iş).

### 5. Örnekleri getir ve karşılaştır
Ders başına bir kez, tüm sorulardaki aday kodlarla çağır:
```bash
$PY $S/ornek_bul.py <ders> <sınıf> <kod1> <kod2> ...     # her bileşenden 2 örnek
$PY $S/ornek_bul.py <ders> <sınıf>                        # bankanın kapsam özeti
```
Çıktıda her bileşenin örnekleri, özetleri, ayırt edici ipuçları ve görsel yolları vardır.

- Önce özet + ipuçlarıyla karşılaştır. Sorunun **görev türü** (tanıma, seçme, kullanma, çıkarım,
  gözden geçirme, yorumlama …) ve soru kökü hangi örneğe benziyor?
- İki bileşen arasında kaldığında o bileşenlerin **örnek görsellerini aç** (Read) ve soruyla yan
  yana değerlendir. Soru başına ~6 görseli geçme.
- Birden çok tutarlı örnek tek örnekten güçlüdür. `yayinevi` etiketli örnekler, Claude'un tamamladığı
  (`yayinevi+claude`, `claude`) örneklerden güçlüdür.
- Örnek bir kanıttır, kural değil. **Karar program metnine göre verilir.** Yayınevleri aynı tür soruyu
  farklı çıktı/bileşenlere bağlayabiliyor; programla açıklanamayan yayınevi tercihlerini (alışkanlıklarını)
  kural yapma. Örnekle program metni çelişiyorsa program metnine uy ve bunu gerekçede belirt.
- Hiç örneği olmayan çıktı/bileşen için yalnızca program metni ve notlarla karar ver; güveni buna göre düşür.

**Test modu:** Kitapçık bankada zaten varsa (değerlendirme amaçlı yeniden etiketleme), kendi
örneklerini dışarıda bırak: `--haric <kaynak-id>`. Aksi hâlde sonuç anlamsızdır.

### 6. Karar ver
Önce şu dört adımı her soru için uygula (geçmiş ölçümlerdeki hataların çoğu bunlar atlandığı için oldu):
1. **Sorunun tamamını gör.** Kök, öncüller ve tüm seçenekler; şekil, grafik, tablo varsa ya da metinde
   kesir/sembol bozuk çıkmışsa (ör. "2 6 5", "4,5µ4") kırpımı aç. Kesilmiş metinle karar verme.
2. **Görevi tek cümleyle yaz:** öğrenci ne yapıyor? (ör. "sözcüğün metindeki anlamını buluyor",
   "modeldeki hatayı düzeltiyor", "enerji türünü belirliyor"). Konu kelimesine ("model", "enerji",
   "çember") değil bu göreve göre seç.
3. **Komşu çıktıları ele:** aynı temadaki yakın çıktıları (kapsam listesinden) yan yana koy; program
   metnindeki fiil ve kapsam farkıyla ele (notlardaki ayrımlar). Hataların çoğu doğru temada yanlış komşu
   çıktıdır.
4. **Bileşeni fiille eşleştir:** görevdeki eylemi bileşen fiilleriyle karşılaştır (tanır / belirler /
   kullanır; varsayımda bulunur / inceler / sınar / önerme sunar; özetler / yeniler / kontrol eder …).

Sonra her soru için:
- En uygun **öğrenme çıktısı**.
- O çıktının bileşenlerinden **tek birincil bileşen** (yayınevleri soru başına tek bileşen atar);
  gerçekten gerekiyorsa bir ikincil bileşeni "ikincil" diye ayrıca belirt.
- **Güven:** *yüksek*: aynı görev türünde yayınevi etiketli örnek(ler) ve program metni aynı yönü
  gösteriyor. *orta*: örnek yok ya da yalnızca dolaylı benzerlik, ama program metni açık.
  *düşük*: adaylar arasında belirgin tereddüt ya da örneklerle çelişki → **"kontrol edilmeli"**.
- **Gerekçe:** bir-iki cümle; dayandığın örnek varsa id'sini yaz (ör. "benzer: eksen-5-sd1-a-04").

### 7. Yayınevi tablosu varsa sonra karşılaştır
Eşleştirmeden sonra kitapçıktaki tabloyla karşılaştır; farkları "Yayınevi tablosuyla farklar"
bölümünde iki görüşün gerekçesiyle listele. Yayınevi kodlarını referansla doğrula.

### 8. Raporla
Her ders için ayrı başlık ve tablo; sonunda kısa özet (ders bazında çıktı dağılımı, kontrol edilmesi
gereken sorular, referansı olmayan dersler, örneği bulunmayan çıktılar).

Makinece okunur hâlini `tmp/test/<ad>/tahmin.json` olarak kaydet:
```json
{"kaynak": "<varsa kaynak-id>", "sinif": 5,
 "sorular": [{"ders": "matematik", "no": 1, "cikti": "MAT.5.3.2.", "bilesenler": ["b"],
              "guven": "yüksek", "dayanak": ["eksen-5-sd1-a-07"]}]}
```
Kitapçık bankadaysa: `$PY $S/degerlendir.py tmp/test/<ad>/tahmin.json --kaynak <kaynak-id>`.

## Derse özgü notlar

- **Türkçe:** Beceri alanları Dinleme/İzleme (T.D), Okuma (T.O), Konuşma (T.K), Yazma (T.Y). Aynı
  başlık birden fazla alanda olabilir; kodu sorunun ölçtüğü beceriye göre seç. Yazılı bir metin
  üzerinden sorulan sorular için önce Okuma (T.O) çıktılarını değerlendir.
- **İngilizce:** Kodlar `ENG.<sınıf>.<tema>.<beceri><no>.`; beceri harfleri ana dosyadaki
  `beceri_harfleri`'nde. Önce temayı bul, sonra o temanın dosyasını aç. Çıktı ve bileşen metinlerini
  programdaki gibi **İngilizce** yaz; gerekçe Türkçe. 7. sınıf da TYMM'ye (ENG.7) göre eşlenir
  (kullanıcı kararı); taslak plan eski programla olduğu için hafta daraltması yapılamaz.

## Çıktı formatı

| Soru | Öğrenme çıktısı | Süreç bileşeni | Güven | Gerekçe |
|------|-----------------|----------------|-------|---------|
| 1    | `<kod>` <çıktı metni> | b) <bileşen metni> | yüksek | … (benzer: <örnek-id>) |

Çıktı ve bileşenleri **her zaman tam cümle** olarak referanstaki metinle yaz; yalnızca harf veya
yalnızca kod yazma. Tablo çok genişlerse her soruyu ayrı başlık altında liste olarak ver.
Kullanıcı isterse `.xlsx` olarak da ver.
