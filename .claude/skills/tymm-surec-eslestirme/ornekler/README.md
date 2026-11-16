# Örnek bankası

Yayınevi kazanım tablolarıyla doğrulanmış soru ↔ öğrenme çıktısı / süreç bileşeni çiftleri.
Ekleme: `tymm-ornek-ekle` skill'i. Kullanım: `scripts/ornek_bul.py`.

```
ornekler/<ders>/<sınıf>.json      etiketler (git'te)
ornekler/<ders>/gorsel/<id>.png   kırpılmış soru görselleri (git DIŞINDA, .gitignore)
```

Görseller yayınevi içeriği olduğu için commit'lenmez. Başka bir makinede görseller yoksa
`ornek_bul.py` "(görsel bu makinede yok)" yazar; özet ve ipuçları yine kullanılabilir. Görselleri
yeniden üretmek için kaynak PDF ile `tymm-ornek-ekle` 3. adımı tekrarlanır.

## `<sınıf>.json`

```json
{
 "ders": "matematik", "sinif": 5,
 "kaynaklar": [
  {"id": "eksen-5-sd1-a", "deneme": "5. Sınıf Süreç Değerlendirme 1", "yayinevi": "Eksen",
   "sinif": 5, "kitapcik": "A", "tarih": null, "tablo_dosyasi": "data.xlsx"}
 ],
 "sorular": [
  {"id": "eksen-5-sd1-a-04", "kaynak": "eksen-5-sd1-a", "no": 4,
   "ozet": "Cetvelle ölçülen uzunluğun sembolle gösterimi seçenekler arasından seçiliyor.",
   "cikti": "MAT.5.3.1.", "bilesenler": ["b"],
   "etiket_kaynagi": "yayinevi",
   "yayinevi_metni": "Nokta, doğru, … uygun olan araç ve teknolojileri belirler.",
   "ipucu": "Gösterimi seçme → b; 'kullanır' (c) değil.",
   "gorsel": "gorsel/eksen-5-sd1-a-04.png"}
 ]
}
```

| Alan | Açıklama |
|---|---|
| `etiket_kaynagi` | `yayinevi`: çıktı + bileşen tablodan. `yayinevi+claude`: çıktı tablodan, bileşeni Claude seçti. `claude`: tablo metni referansla eşleşmedi (serbest etiket, eski program); çıktı + bileşeni Claude seçti. |
| `yayinevi_metni` / `yayinevi_kodu` | Tablodaki ham değer (izlenebilirlik için). |
| `yakin_ifade` | Tablo metni programdan küçük farkla yazılmış; eşleşme toleransla kabul edildi. |
| `ipucu` | Ayırt edici kural (isteğe bağlı). Etiketlemede gösterilir. |
| `not` | Şüpheli/tartışmalı durumlar. |

## Ara şablon: `tablo.json`

`yayinevi_tablo.py` çıktısı; Claude tamamlar, `ornek_ekle.py` bankaya yazar.

```json
{"kaynak": {"id": "...", "deneme": "...", "yayinevi": "...", "sinif": 5, "kitapcik": "A",
            "tarih": null, "tablo_dosyasi": "..."},
 "satirlar": [
  {"ders": "matematik", "no": 4, "yayinevi_metni": "...", "duzey": "bilesen",
   "cikti": "MAT.5.3.1.", "bilesenler": ["b"], "etiket_kaynagi": "yayinevi",
   "ozet": "...", "ipucu": "..."}
 ]}
```
`ders`: klasör adı (`matematik`, `turkce` …); referansı olmayan derslerde tablodaki ad kalır ve
`duzey: "referans yok"` olur.
