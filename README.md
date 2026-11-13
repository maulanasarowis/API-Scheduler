# API Scheduler

Aplikasi pribadi untuk menjalankan kumpulan API secara otomatis sesuai jadwal.
Stack: FastAPI, PostgreSQL (SQLAlchemy), APScheduler, HTTPX, Bootstrap 5.

## Instalasi (Windows)

1. Pasang Python 3.10+ dan PostgreSQL.
2. Buat database kosong, misalnya lewat pgAdmin atau psql:
   ```
   CREATE DATABASE api_scheduler;
   ```
3. Buka terminal di folder project, lalu:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```
4. Edit `.env`, sesuaikan `DATABASE_URL` (user, password, nama database) dan `TIMEZONE`.
5. Jalankan:
   ```
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
6. Buka http://127.0.0.1:8000

Tabel dibuat otomatis saat aplikasi pertama kali berjalan.

## Penggunaan

- **Daftar API**: klik *Tambah API*, isi nama, URL, method, headers/body (JSON, opsional),
  timeout, status aktif, lalu tambahkan jam eksekusi (bisa lebih dari satu per hari).
- Tombol aksi: **Jalankan Sekarang**, **Aktif/Nonaktif**, **Edit**, **Hapus**.
- **Riwayat Eksekusi**: filter berdasarkan tanggal, API, dan status. Tombol *Detail* menampilkan response dan error.
- Perubahan jadwal/status langsung berlaku tanpa restart.

## Catatan penting

- Scheduler hanya berjalan selama aplikasi Python aktif. Biarkan terminal tetap terbuka
  (atau jalankan lewat Task Scheduler Windows saat startup).
- Jangan gunakan `--reload` atau `--workers` lebih dari 1, agar jadwal tidak berjalan ganda.
- Jadwal yang terlewat saat aplikasi mati tidak dijalankan susulan (toleransi 60 detik).
- Sukses = HTTP 2xx. Response disimpan maksimal 20.000 karakter.
- Aplikasi tanpa login, sebaiknya hanya diakses dari `127.0.0.1`.

## Struktur

```
app/
  main.py        # FastAPI + start scheduler
  config.py      # .env, timezone
  database.py    # koneksi SQLAlchemy
  models.py      # api_configs, api_schedules, api_execution_logs
  executor.py    # menjalankan request HTTP + simpan log
  scheduler.py   # APScheduler, sinkron dari database
  routes.py      # halaman + endpoint JSON
  templates/     # HTML (Bootstrap 5)
  static/        # CSS & JS
```
