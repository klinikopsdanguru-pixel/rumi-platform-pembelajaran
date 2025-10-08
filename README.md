# Proyek Platform Pembelajaran RUMI

Ini adalah proyek aplikasi web untuk platform pembelajaran IPA terpadu bernama RUMI (Ruang Mandiri IPA), yang dibangun menggunakan Flask dan SQLAlchemy.

## Instalasi

1.  Pastikan Anda memiliki Python 3.
2.  Buat *virtual environment*:
    `python -m venv venv`
3.  Aktifkan *virtual environment*:
    * Windows: `.\venv\Scripts\activate`
    * Mac/Linux: `source venv/bin/activate`
4.  Install semua pustaka yang dibutuhkan:
    `pip install -r requirements.txt`
5.  Buat database (hanya untuk pertama kali):
    * Jalankan `flask shell`
    * Ketik `from app import db`
    * Ketik `db.create_all()`
    * Ketik `exit()`

## Menjalankan Aplikasi
Setelah instalasi, jalankan aplikasi dengan perintah:
`python app.py`

Aplikasi akan berjalan di `http://127.0.0.1:5000`.