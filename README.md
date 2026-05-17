# Tureng
Bu proje [Tureng](https://tureng.com/tr/turkce-ingilizce) Türkçe İngilizce Sözlüğü'nün veri tabanının offline bir kopyasını oluşturmayı amaçlar. Bu veri tabanını oluşturmak için 2 adımlı bir strateji izlenir. Öncelikle [Tureng](https://tureng.com/tr/turkce-ingilizce) sitesinde arama kısmındaki kelimeler "brute force" mantığıyla tek tek toplanır. Ardından bu kelimeler üzerinden veri tabanı oluşturulmaya başlanır. Veri tabanı oluşturulurken bulunan yeni kelimeler de bu listeye eklenir, ve bu şekilde ulaşılabilen bütün kelimeler veri tabanına alınmış olur.

## Birinci Adım
Elimizde henüz kelime listesi olmadığı için öncelikle veri tabanını oluşturmaya başlayacağımız kelime listesini oluşturmalıyız. Bunun için aşağıdaki kod kullanılır. ``find_all_words_starting_with`` methodu kendisine prefix (ön ek) olarak verilen yazının sonuna farklı farklı karakterler ekleyerek bu yeni prefix'leri tek tek dener ve ekrana her denemede bulunan toplam kelime sayısını ve denenecek kelime sayısını yazdırır.

```python
import json
import tureng

trng = tureng.Tureng()

for chracter in '0123456789abcçdefgğhıijklmnoöpqrsştuüvwxyz':
   print(chracter)
   with open(f'tureng/{chracter}.json', 'w') as fp:
       json.dump(trng.find_all_words_starting_with(chracter), fp)
```

Her harf için bulunan bütün kelimeler tek bir json dosyasına konulur. 5/17/2026 tarihinde benim tarafımdan oluşturulan bu kelime listesine [tureng_words.json](https://github.com/helallao/tureng/releases) dosyasından ulaşabilirsiniz.

## İkinci Adım
Daha sonra oluşturulan bu kelime listesi kullanılarak Türkçe/İngilizce ve İngilizce/Türkçe şeklinde olmak üzere iki bölümden oluşan bir veri tabanı oluşturulur. Bunun için aşağıdaki kod kullanılır. ``update_database`` methodu kendisine verilen "wordlist_path", "database_path" ve "completed_words_path" argümanlarındaki dosyaları kullanarak veri tabanını oluşturur. "wordlist_path" dosyası birinci adımda toplanan kelime listesidir, "database_path" veri tabanı dosyasıdır. Eğer henüz oluşturmadıysanız içeriği ``{"ing": {}, "tur": {}}`` şeklinde olmalıdır. "completed_words_path" ise şu ana kadar veri tabanına eklenmiş kelimelerin listesidir. Eğer henüz oluşturmadıysanız içeriği ``[]`` şeklinde olmalıdır. Kodları çalıştırdığınız zaman her defasında "max_word_limit" argümanına verdiğiniz sayıda kelime veri tabanına eklenir ve dosyalar güncellenir. Veri tabanını oluşturmak uzun süreceği için kodları durdurmak istediğinizde o anki işlem henüz 100%'e ulaşmadan durdurabilirsiniz. "completed_words_path" dosyasının boyutu "wordlist_path" dosyasının boyutuna eşitlendiği zaman bütün kelimeler veri tabanına eklenmiş demektir. 5/17/2026 tarihinde benim tarafımdan oluşturulan veri tabanına [tureng_database.json](https://github.com/helallao/tureng/releases) dosyasından ulaşabilirsiniz.

```python
import tureng

trng = tureng.Tureng()
trng.update_database('tureng_words.json', 'tureng_database.json', 'tureng_completed_words.json', max_word_limit=10_000)
```

## Sonuç
Oluşturulan veri tabanı ile offline olarak kelimelerin anlamlarına bakabilirsiniz,

```python
import json

with open('tureng_database.json') as fp:
    database = json.load(fp)

print(database['ing']['extermination'])
# ['imha', 'yok etme', 'ortadan kaldırma', 'kökünü kazıma', 'imha etme', 'imha edilme']

print(database['tur']['imha'])
# ['extermination', 'destruction', 'annihilation', 'disposal', 'holocaust', 'demolition', 'deracination', 'demolishment', 'eradication', 'extirpation', 'extinction', 'wipeout', 'wipe-out', 'demo', 'amortisation', 'amortization']
```
