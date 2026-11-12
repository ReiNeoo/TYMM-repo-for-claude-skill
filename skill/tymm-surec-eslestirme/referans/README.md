# Referans verisi

Dosyalar `tymm_programmes/` altındaki kaynaklardan betiklerle üretilir; elle içerik yazılmaz.
Hepsini yeniden üretmek için (Git Bash, repo kökü): `bash scripts/referans_hepsi.sh`

- Çıktı kodu, çıktı metni, süreç bileşenleri, tema adı, ders saati → **program PDF'i**
- `plan_haftalari`, `plan.haftalar` → **MEB taslak çerçeve yıllık planı**
- `kaynak_notlari` → kaynakta eksik/farklı olan durumlar (ör. bileşen verilmemiş çıktılar).
  Skill bu notlara uyar.

Kapsam: 5–7. sınıflar. Ders klasörleri: `matematik`, `fen-bilimleri`, `sosyal-bilgiler`,
`turkce`, `ingilizce`. Doğrulanmış ayrım kuralları: `<ders>/<sınıf>-notlar.md`.

## Matematik, Fen Bilimleri, Sosyal Bilgiler: `<ders>/<sınıf>.json`

```json
{
  "ders": "Matematik", "sinif": 5, "kaynak_pdf": "…pdf", "not": "…",
  "kaynak_notlari": [],
  "plan": { "kaynak": "…xlsx", "sayfa": "5.Sınıf", "haftalar": { "1": "14-18 Eylül" } },
  "temalar": [
    {
      "islenis_sirasi": 1, "ad": "<tema adı>", "ders_saati": 0, "sayfa": 0,
      "ciktilar": [
        {
          "kod": "<kod>", "metin": "<çıktı metni>", "sayfa": 0,
          "surec_bilesenleri": [ { "harf": "a", "metin": "<bileşen metni>" } ],
          "plan_haftalari": [1, 2]
        }
      ]
    }
  ]
}
```

## Türkçe: `turkce/<sınıf>.json` + `turkce/<sınıf>/<beceri>.json`

Aynı öğrenme çıktısı birden fazla temada yer alabildiği için çıktılar bir kez listelenir;
süreç bileşenleri programın "9. Tablo"sundan alınır ve beceri alanına göre ayrı dosyadadır.

```json
{
  "ders": "Türkçe", "sinif": 5, "kaynak_notlari": ["…"], "plan": { … },
  "temalar": [ { "islenis_sirasi": 1, "ad": "OYUN DÜNYASI", "ders_saati": 34, "sayfa": 0,
                 "kodlar": ["T.D.5.3.", "T.O.5.2.", "…"] } ],
  "ciktilar": [ { "kod": "T.O.5.6.", "beceri_alani": "Okuma", "metin": "…",
                  "plan_haftalari": [1, 2], "bilesen_dosyasi": "5/okuma.json" } ]
}
```

`5/okuma.json`: `{ "ciktilar": [ { "kod", "metin", "tablo9_sayfa", "surec_bilesenleri": [ … ] } ] }`

## İngilizce: `ingilizce/<sınıf>.json` + `ingilizce/<sınıf>/tema-N.json`

```json
{
  "ders": "İngilizce", "sinif": 5, "kaynak_notlari": [], "beceri_harfleri": { "L": "Listening", … },
  "plan": { … },
  "temalar": [ { "islenis_sirasi": 1, "ad": "SCHOOL LIFE", "ders_saati": null, "sayfa": 0,
                 "plan_haftalari": [4, 5, 6], "bilesen_dosyasi": "5/tema-1.json",
                 "kodlar": ["ENG.5.1.L1.", "…"] } ]
}
```

`5/tema-1.json`: `{ "ciktilar": [ { "kod", "metin", "sayfa", "surec_bilesenleri": [ … ] } ] }`
