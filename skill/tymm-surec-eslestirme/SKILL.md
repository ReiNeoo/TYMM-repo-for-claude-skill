---
name: tymm-surec-eslestirme
description: Ortaokul deneme sınavı kitapçıklarındaki (PDF) soruları Türkiye Yüzyılı Maarif Modeli (TYMM) öğretim programındaki öğrenme çıktıları ve süreç bileşenleriyle eşleştirir. Tek dersli testler ve tüm dersleri içeren genel denemeler için çalışır. Kullanıcı bir deneme, test, sınav, süreç değerlendirme ya da soru kitapçığı yükleyip soruların hangi öğrenme çıktısına, kazanıma veya süreç bileşenine ait olduğunu sorduğunda; "soru-kazanım eşleştirmesi", "süreç bileşeni analizi", "TYMM eşleştirme" istediğinde kullan. Dersler - Türkçe, Matematik, Fen Bilimleri, Sosyal Bilgiler, İngilizce (5-7. sınıf).
---

# TYMM Süreç Bileşeni Eşleştirme

Bu skill, bir deneme kitapçığındaki her soruyu TYMM öğretim programındaki **öğrenme çıktısı**
(kod + metin) ve **süreç bileşenleri** (a, b, c, ç, …) ile eşleştirir.

## Temel kurallar

- Öğrenme çıktısı kodlarını ve süreç bileşeni metinlerini **yalnızca** `referans/` altındaki
  JSON dosyalarından al. Ezberden kod veya metin yazma.
- Her referans dosyasındaki `kaynak_notlari` alanını oku ve uy. Örneğin bazı Türkçe çıktılar için
  programda süreç bileşeni verilmemiştir; o zaman yalnızca öğrenme çıktısını yaz, bileşen uydurma.
- İlgili ders/sınıf için referans yoksa (ör. Din Kültürü ve Ahlak Bilgisi, 8. sınıf, İnkılap
  Tarihi) o dersin sorularını "referans yok" diye listele, eşleştirme yapma.
- TYMM terminolojisini kullan ("öğrenme çıktısı", "süreç bileşeni"). Kullanıcı "kazanım" derse
  anla, ama yanıtta TYMM terimlerini kullan.

## Referans dosyaları

Ders klasörleri: `turkce`, `matematik`, `fen-bilimleri`, `sosyal-bilgiler`, `ingilizce`.
Her ders için önce **ana dosyayı** oku: `referans/<ders>/<sınıf>.json`.

| Ders | Ana dosyada | Süreç bileşenleri |
|---|---|---|
| Matematik, Fen Bilimleri, Sosyal Bilgiler | `temalar[].ciktilar[]` (kod, metin, bileşenler, plan haftaları) | Ana dosyada |
| Türkçe | `temalar[].kodlar` + `ciktilar[]` (her kod bir kez: metin, beceri alanı, plan haftaları) | `bilesen_dosyasi` → `<sınıf>/okuma.json`, `dinleme-izleme.json`, `konusma.json`, `yazma.json` |
| İngilizce | `temalar[]` (ad, plan haftaları, kodlar) | `bilesen_dosyasi` → `<sınıf>/tema-N.json` (çıktı metni + bileşenler) |

Ana dosyayla aday çıktıları seç; bileşenler için yalnızca gereken parça dosyasını aç.
Varsa `referans/<ders>/<sınıf>-notlar.md` dosyasını da oku: kullanıcı/yayınevi tarafından
doğrulanmış ayrım kurallarıdır ve genel değerlendirmenin önüne geçer.

## İş akışı

1. **Kitapçığı tanı.** Sınıf, kitapçık türü (A, B …), sınav adı ve tarih. Kitapçık birden fazla
   ders içeriyorsa ders bölümlerini başlıklardan ayır; **her derste soru numaraları 1'den
   başlar**, bu yüzden soruları her zaman "ders + soru no" ile an. Bilgi kitapçıktan
   anlaşılmıyorsa kullanıcıya sor.
2. **Soruları oku.** Sayfa sayfa oku; şekil, grafik, tablo ve metinleri de dikkate al.
   Taranmış (metin katmanı olmayan) PDF'ler olağandır; sayfaları görsel olarak oku.
   Sayfa sırası karışık olabilir; soruları ders içinde **soru numarasına** göre sırala.
   Birden fazla soruya ait ortak metin/görsel ("3 ve 4. soruları … göre cevaplayınız") her iki
   soru için de kullanılır. Kapaktaki soru sayısıyla kitapçıktaki soru sayısı farklıysa belirt.
3. **Referansı yükle ve kapsamı daralt.** Her ders için ana dosyayı oku. Tarih verildiyse
   `plan.haftalar` (hafta → tarih aralığı) ile haftayı bul; `plan_haftalari` o haftaya kadar olan
   öğrenme çıktılarını öncelikli aday say. Tarih yok ama sınav adı ipucu veriyorsa (ör. "Süreç
   Değerlendirme – 1" → yılın ilk haftaları) kapsamı buna göre tahmin et ve varsayımı raporda
   belirt. Kapsam dışı bir çıktıyla eşleşme gerekirse not et.
4. **Eşleştir.** Her soru için:
   - En uygun öğrenme çıktısını seç.
   - O çıktının süreç bileşenlerinden soruyla en iyi örtüşen **tek birincil bileşeni** seç
     (yayınevleri soru başına tek bileşen atar). Gerçekten gerekiyorsa bir ikincil bileşeni
     ayrıca ve "ikincil" diye belirt.
   - Güven düzeyi ver: **yüksek / orta / düşük**; düşük güvenlileri **"kontrol edilmeli"** işaretle.
   - Seçimin gerekçesini bir-iki cümleyle yaz.
5. **Yayınevi tablosu varsa sonra karşılaştır.** Kitapçıkta yayınevinin kazanım/öğrenme çıktısı
   tablosu veya cevap anahtarı bulunabilir. Eşleştirmeyi **önce bu tabloya bakmadan** yap; ardından
   karşılaştır ve farklı olan soruları "Yayınevi tablosuyla farklar" bölümünde iki görüşün
   gerekçesiyle listele. Yayınevi kodlarını referansla doğrula; referansta olmayan ya da eski
   programa ait kodları belirt.
6. **Raporla.** Her ders için ayrı başlık ve tablo; sonunda kısa özet (ders bazında çıktı dağılımı,
   kontrol edilmesi gereken sorular, referansı olmayan dersler).

## Derse özgü notlar

- **Türkçe:** Öğrenme çıktıları beceri alanlarına ayrılır: Dinleme/İzleme (T.D), Okuma (T.O),
  Konuşma (T.K), Yazma (T.Y). Aynı başlık birden fazla alanda olabilir (ör. "Bilgilendirici
  metinde …" hem T.D hem T.O); kodu sorunun ölçtüğü beceriye göre seç. Yazılı bir metin
  üzerinden sorulan sorular için önce Okuma (T.O) çıktılarını değerlendir *(başlangıç varsayımı;
  doğrulanmış örnekle güncellenecek)*.
- **İngilizce:** Kodlar `ENG.<sınıf>.<tema>.<beceri><no>.` biçimindedir; beceri harfleri ana
  dosyadaki `beceri_harfleri` alanında. Önce temayı (konu/kelime alanı) bul, sonra o temanın
  dosyasını aç. Çıktı ve bileşen metinlerini programdaki gibi **İngilizce** yaz; gerekçe Türkçe.
  7. sınıf için `kaynak_notlari`'ndaki uyarıya bak: 2026-2027'de 7. sınıf İngilizce eski programla
  okutuluyor olabilir; eşleştirmeden önce kullanıcıya sor.

## Çıktı formatı

Her ders için:

| Soru | Öğrenme çıktısı | Süreç bileşeni | Güven | Gerekçe |
|------|-----------------|----------------|-------|---------|
| 1    | `<kod>` <çıktı metni> | <bileşen metni> | yüksek | … |

Öğrenme çıktısını ve süreç bileşenlerini **her zaman tam cümle olarak** referans dosyasındaki
metinle yaz; yalnızca harf (a, b, c) veya yalnızca kod yazma. Harf, cümlenin önünde etiket
olarak kalabilir. Tablo çok genişleyecekse her soruyu ayrı başlık altında liste olarak ver.

Kullanıcı isterse tabloyu `.xlsx` olarak da ver.
