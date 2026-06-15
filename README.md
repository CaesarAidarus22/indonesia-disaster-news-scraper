# Scraper Berita Bencana Indonesia

Project ini dibuat untuk mengumpulkan artikel berita bencana berbahasa Indonesia sebagai bahan dataset NLP/NER untuk proyek:

**Implementasi Fine-Tuning IndoBERT dalam Ekstraksi Informasi Bencana Berbahasa Indonesia**

Scraper hanya menyimpan artikel yang lolos dua filter utama:

1. Mengandung keyword bencana.
2. Mengandung indikasi lokasi di Indonesia.
3. Mengandung sinyal kejadian bencana aktual atau dampak bencana.

Artikel bencana luar negeri tidak disimpan. Jika artikel mengandung sinyal negara luar dan hanya menyebut lokasi generik seperti `Indonesia` atau `RI`, artikel akan ditolak agar kasus seperti bantuan KBRI untuk bencana luar negeri tidak masuk dataset.

## Website Target

- BNPB.go.id
- Kompas.com
- Detik.com
- Tempo.co
- Republika.co.id
- Kumparan.com
- Liputan6.com
- CNNIndonesia.com
- BNPB.go.id, nonaktif secara default dan hanya aktif jika memakai `--include-bnpb`
- Antara News, nonaktif secara default dan hanya aktif jika memakai `--include-antara`

## Struktur Folder

```text
.
├── main.py
├── requirements.txt
├── README.md
├── scrapers/
│   ├── __init__.py
│   ├── base.py
│   └── sources.py
├── utils/
│   ├── __init__.py
│   ├── filters.py
│   ├── http.py
│   ├── storage.py
│   └── text.py
└── data/
    ├── raw/
    │   ├── example_indonesia_disaster_news.csv
    │   └── example_indonesia_disaster_news.json
    └── processed/
```

Modul scraper tambahan:

- `scrapers/tempo.py`
- `scrapers/republika.py`
- `scrapers/kumparan.py`
- `scrapers/sitemap.py`

## Install Dependency

Aktifkan virtual environment jika sudah punya, lalu install dependency:

```bash
pip install -r requirements.txt
```

## Menjalankan Scraping

Perintah dasar:

```bash
python main.py
```

Perintah dengan batas jumlah URL per sumber dan delay request:

```bash
python main.py --max-links-per-source 50 --delay 2
```

Output akan disimpan otomatis ke:

```text
data/raw/indonesia_disaster_news_YYYYMMDD_HHMMSS.csv
data/raw/indonesia_disaster_news_YYYYMMDD_HHMMSS.json
```

Argumen opsional:

- `--output-dir`: folder output, default `data/raw`
- `--max-pages`: jumlah template halaman pencarian per keyword, default `1`
- `--max-links-per-source`: maksimum URL artikel yang diparse per sumber, default `25`
- `--archive-days`: coba crawling arsip N hari terakhir, contoh `--archive-days 365`
- `--delay`: jeda antar request dalam detik, default `1.5`
- `--timeout`: timeout request dalam detik, default `15`
- `--include-antara`: aktifkan Antara News secara manual. Secara default Antara tidak dipakai.
- `--include-bnpb`: aktifkan BNPB.go.id secara manual. Secara default BNPB tidak dipakai karena endpoint pencariannya dapat mengembalikan error 500.
- `--keywords`: keyword pencarian manual

Contoh:

```bash
python main.py --keywords banjir "gempa bumi" longsor kebakaran --max-links-per-source 30
```

Contoh crawling arsip 1 tahun terakhir:

```bash
python main.py --archive-days 365 --max-links-per-source 200 --delay 2
```

Command uji kecil Liputan6:

```bash
python main.py --keywords banjir --max-links-per-source 20
```

Archive crawling melakukan pre-filter URL sebelum artikel diparse. URL dari kanal seperti `/topik/`, `/pandangan/`, `/opini/`, `/cekfakta/`, `/gaya-hidup/`, `/otomotif/`, `/properti/`, `/hiburan/`, `/bola/`, `/sport/`, `/zodiak/`, dan `/feature/` ditolak sejak tahap link collection. Kanal umum seperti nasional, regional, peristiwa, news, dan lingkungan tetap harus memiliki hint bencana pada URL atau anchor text, kecuali halaman/tag bencana.

Contoh jika ingin mengaktifkan Antara News secara manual:

```bash
python main.py --include-antara
```

Contoh jika ingin mengaktifkan BNPB secara manual:

```bash
python main.py --include-bnpb
```

## Format Output Dataset

Setiap artikel disimpan dengan kolom berikut:

- `id`
- `title`
- `url`
- `source`
- `published_date`
- `author`
- `content`
- `disaster_keywords_found`
- `indonesia_location_keywords_found`
- `event_score`
- `rejection_reason`
- `scraped_at`

Contoh CSV dan JSON tersedia di:

- `data/raw/example_indonesia_disaster_news.csv`
- `data/raw/example_indonesia_disaster_news.json`

## Aturan Filtering

Keyword bencana yang digunakan:

```text
banjir, gempa, gempa bumi, tsunami, longsor, tanah longsor, kebakaran,
erupsi, gunung meletus, puting beliung, kekeringan, abrasi,
gelombang tinggi, korban jiwa, pengungsi, evakuasi, kerusakan,
bantuan logistik, BNPB, BPBD
```

Keyword lokasi Indonesia yang digunakan:

```text
Indonesia, RI, Aceh, Sumatera, Sumut, Sumbar, Riau, Jambi, Bengkulu,
Lampung, Bangka Belitung, Kepulauan Riau, Jakarta, Jawa Barat,
Jawa Tengah, Jawa Timur, Banten, Yogyakarta, Bali, NTB, NTT,
Kalimantan, Sulawesi, Maluku, Papua, Banda Aceh, Medan, Padang,
Pekanbaru, Palembang, Bandung, Semarang, Surabaya, Denpasar,
Mataram, Kupang, Pontianak, Banjarmasin, Samarinda, Balikpapan,
Makassar, Manado, Ambon, Jayapura, Kabupaten, Kota, Provinsi,
BNPB, BPBD
```

Artikel hanya disimpan jika:

- `is_disaster_article()` menemukan minimal satu keyword bencana.
- `is_indonesia_related_article()` menemukan minimal satu keyword lokasi Indonesia.
- `is_actual_disaster_event()` menemukan sinyal kejadian atau dampak bencana aktual.
- URL belum pernah disimpan sebelumnya.
- Judul dan isi artikel berhasil diparse.

Filter kejadian aktual menerima artikel yang memiliki minimal satu keyword event:

```text
terjadi, melanda, mengguncang, merendam, terdampak, tewas,
meninggal, rusak, mengungsi, evakuasi, jebol, hanyut
```

Artikel akan ditolak jika dominan membahas topik non-kejadian:

```text
penelitian, riset, studi, sejarah, purba, mitigasi, pencegahan,
sosialisasi, pembangunan, revitalisasi, normalisasi, proyek,
perencanaan, rapat, koordinasi, pelatihan, simulasi, monitoring,
pos pantau, sistem peringatan dini, evaluasi, anggaran,
proyek infrastruktur, edukasi, geologi, geologis
```

## Alur Scraping

1. `main.py` membangun scraper untuk setiap sumber berita.
2. `get_article_links()` mencari URL kandidat dari arsip, halaman kategori, sitemap, dan pencarian keyword. URL disimpan ke `set()` per source agar link yang sama dari keyword/kategori berbeda tidak ditambahkan ulang.
3. `parse_article()` mengambil judul, tanggal, penulis, dan isi artikel.
4. `clean_text()` membersihkan whitespace dan karakter HTML.
5. `is_disaster_article()` mengecek keyword bencana.
6. `is_indonesia_related_article()` mengecek indikasi lokasi Indonesia.
7. `is_actual_disaster_event()` mengecek apakah artikel benar-benar melaporkan kejadian atau dampak bencana.
8. `remove_duplicate_urls()` menghapus URL duplikat.
9. `save_to_csv()` dan `save_to_json()` menyimpan dataset.

## Catatan Pengembangan

Website berita sering mengubah struktur HTML. Jika artikel dari salah satu sumber kosong, perbarui selector pada `scrapers/sources.py` atau modul scraper sumber terkait.

Scraper memeriksa `robots.txt` sebelum mengambil halaman pencarian, sitemap, kategori, dan artikel. Jeda request dapat diatur lewat `--delay`.

Log scraping menampilkan `unique_urls_found`, `duplicate_urls_skipped`, `archive_urls_found`, `archive_urls_skipped`, dan `archive_urls_after_filter` untuk memantau apakah run memperluas artikel bencana unik atau hanya menambah URL mentah.

Dataset ini dapat diproses lanjut di `data/processed/` untuk anotasi NER dengan label:

- `DISASTER`
- `LOCATION`
- `CASUALTIES`
- `DATE_TIME`
- `SUPPLIES`
- `DAMAGE`
