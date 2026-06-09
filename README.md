# AI Stock Analyzer Bot

Bot analisa saham Indonesia berbasis FastAPI dan Telegram. Aplikasi mengambil data pasar,
menghitung indikator teknikal, mengambil fundamental yang tersedia, lalu meminta satu atau
beberapa model AI untuk membuat analisa edukatif. Hasil analisa dan scan disimpan di MySQL.

> Aplikasi ini tidak menjanjikan keuntungan dan bukan nasihat keuangan resmi. Data Yahoo
> Finance dapat tertunda, tidak lengkap, atau berbeda dari data bursa/broker.

## Fitur

- Analisa saham IDX tunggal dengan suffix `.JK` otomatis.
- Scan grup IHSG, LQ45, IDX30, IDX80, JII, High Dividend, ESG, dan seluruh daftar.
- Provider OpenAI, Gemini, Claude, dan DeepSeek; provider tanpa API key dilewati.
- Multi-AI paralel dan kesimpulan gabungan.
- MA5/20/50/100/200, RSI14, MACD, support/resistance, 52-week range, volume ratio.
- Fundamental Yahoo Finance dan struktur sentimen yang siap dihubungkan ke News API.
- Watchlist, history, batas penggunaan harian, cache data, dan error handling.
- REST API opsional dengan proteksi `X-API-Key`.
- Bootstrap tabel otomatis, seed grup saham, APScheduler, dan systemd untuk VPS.

## Struktur Penting

```text
app/
  bot/        Telegram handlers
  data/       Daftar grup saham yang dapat diedit
  models/     Model SQLAlchemy
  prompts/    Prompt analisa, scan, dan multi-AI
  services/   Market data, indikator, provider AI, analisa, dan scan
deploy/       Unit systemd
migrations/   Bootstrap SQL MySQL
tests/        Unit test inti
```

## 1. Instalasi Lokal

Persyaratan: Python 3.10+, MySQL 8+, dan token Telegram dari `@BotFather`.

```bash
git clone <repository-url> ai-stock-analyzer-bot
cd ai-stock-analyzer-bot
python -m venv venv
```

Linux/macOS:

```bash
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## 2. Membuat Database MySQL

Cara cepat dengan migration bootstrap:

```bash
mysql -u root -p < migrations/001_initial.sql
```

Atau buat database dan user khusus:

```sql
CREATE DATABASE stockbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'stockbot'@'localhost' IDENTIFIED BY 'password-kuat';
GRANT ALL PRIVILEGES ON stockbot.* TO 'stockbot'@'localhost';
FLUSH PRIVILEGES;
```

Tabel juga dibuat otomatis saat aplikasi pertama kali berjalan. SQL bootstrap tetap disediakan
untuk instalasi yang ingin menyiapkan skema lebih dahulu.

## 3. Mengisi `.env`

Salin `.env.example` menjadi `.env`, lalu isi minimal:

```dotenv
DATABASE_URL=mysql+pymysql://stockbot:password-kuat@localhost:3306/stockbot?charset=utf8mb4
TELEGRAM_BOT_TOKEN=token-dari-botfather
OPENAI_API_KEY=api-key-anda
DEFAULT_AI_PROVIDER=openai
API_ACCESS_KEY=buat-random-secret-untuk-rest-api
```

API key tidak pernah ditulis di source code. Jangan commit `.env`. Untuk produksi, gunakan
password MySQL dan `API_ACCESS_KEY` yang kuat.

Model setiap provider dapat diubah melalui `OPENAI_MODEL`, `GEMINI_MODEL`, `CLAUDE_MODEL`, dan
`DEEPSEEK_MODEL`. Default proyek memakai model cepat/hemat yang tersedia pada Juni 2026. Model
provider dapat berubah atau dihentikan; gunakan model yang tersedia di akun Anda.

## 4. Menjalankan Bot dan API

```bash
python run.py
```

API tersedia di `http://127.0.0.1:8000`; dokumentasi interaktif di `/docs`. Telegram polling
berjalan dalam proses yang sama jika `TELEGRAM_BOT_TOKEN` terisi.

Contoh API:

```bash
curl http://127.0.0.1:8000/health
curl -H "X-API-Key: secret" http://127.0.0.1:8000/stocks/BBCA
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: secret" \
  -d '{"code":"BBCA","telegram_id":123456}' http://127.0.0.1:8000/analyze
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: secret" \
  -d '{"group_name":"LQ45","limit":10}' http://127.0.0.1:8000/scan
```

Endpoint `/scan` mengembalikan HTTP `202` dan job ID. Pantau progress dengan:

```bash
curl -H "X-API-Key: secret" http://127.0.0.1:8000/scan/jobs/JOB_ID
```

Jalankan test:

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
```

## 5. Deploy ke VPS Ubuntu

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip mysql-server git
sudo useradd --system --create-home --shell /usr/sbin/nologin stockbot
sudo mkdir -p /var/www/ai-stock-analyzer-bot
sudo chown -R stockbot:stockbot /var/www/ai-stock-analyzer-bot
sudo -u stockbot git clone <repository-url> /var/www/ai-stock-analyzer-bot
cd /var/www/ai-stock-analyzer-bot
sudo -u stockbot python3 -m venv venv
sudo -u stockbot venv/bin/pip install -r requirements.txt
sudo -u stockbot cp .env.example .env
sudo chmod 600 .env
```

Isi `.env`, siapkan MySQL, lalu pasang systemd:

```bash
sudo cp deploy/ai-stock-analyzer-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-stock-analyzer-bot
sudo systemctl status ai-stock-analyzer-bot
journalctl -u ai-stock-analyzer-bot -f
```

Jika REST API akan dibuka ke internet, letakkan Nginx/Caddy dengan HTTPS di depannya, batasi
firewall, dan selalu isi `API_ACCESS_KEY`. Endpoint `/health` sengaja tetap publik.

## 6. Menambahkan Daftar Saham Baru

Edit `app/data/stock_groups.json`. Kode ditulis tanpa `.JK`:

```json
"GRUP_BARU": {
  "description": "Daftar yang dikelola admin.",
  "stocks": ["BBCA", "BBRI"]
}
```

Restart aplikasi setelah mengubah file. Pada startup, daftar JSON disinkronkan ke tabel grup.
Komposisi indeks yang disertakan adalah sampel dan harus diperbarui admin saat indeks berubah.

## 7. Mengganti AI Provider

Isi API key provider dan ubah provider default:

```dotenv
GEMINI_API_KEY=...
DEFAULT_AI_PROVIDER=gemini
```

Pilihan: `openai`, `gemini`, `claude`, `deepseek`. Jika provider default tidak memiliki key,
aplikasi memakai provider aktif pertama. Jika tidak ada key sama sekali, analisa menampilkan
error konfigurasi yang jelas.

## 8. Mengaktifkan Multi AI

Isi minimal dua API key, lalu:

```dotenv
ENABLE_MULTI_AI=true
SUMMARY_AI_PROVIDER=openai
```

Analisa lengkap dikirim paralel ke semua provider aktif. Hasil tiap provider disimpan, kemudian
provider ringkasan membuat kesimpulan final. Scan cepat tetap memakai satu provider agar biaya,
waktu, dan rate limit tetap terkendali.

## Command Telegram

`/start`, `/help`, `/analyze KODE`, `/scan`, `/scan_lq45`, `/scan_idx30`, `/scan_idx80`,
`/scan_jii`, `/scan_dividend`, `/scan_esg`, `/scan_all`, `/scan_status JOB_ID`, `/watchlist`, `/addwatch KODE`,
`/removewatch KODE`, `/history`, `/settings`.

## Catatan Operasional

- `MAX_ANALYSIS_PER_DAY` dan `MAX_SCAN_PER_DAY` membatasi penggunaan per user Telegram.
- `MAX_SCAN_STOCKS` membatasi jumlah saham yang diproses per request.
- `SCAN_DELAY_SECONDS` memberi jeda antar saham untuk mengurangi risiko rate limit.
- Berita tersedia jika `NEWS_API_KEY` diisi; tanpa key sistem menampilkan keterbatasan data.
- Satu proses polling Telegram harus dijalankan. Jangan menyalakan beberapa replica dengan token
  yang sama kecuali mengganti integrasi menjadi webhook.

## Production Hardening

Versi ini memiliki retry exponential backoff untuk Yahoo Finance, AI provider, dan News API;
output AI terstruktur dengan fallback aman; persistent scan queue; progress job; readiness;
Prometheus metrics; Alembic; backup; serta health-check systemd.

Konfigurasi opsional:

```dotenv
METRICS_ACCESS_KEY=secret-metrics
NEWS_API_KEY=
EXTERNAL_REQUEST_MAX_ATTEMPTS=3
EXTERNAL_REQUEST_BACKOFF_SECONDS=1
SCAN_WORKER_COUNT=1
SCAN_JOB_RETENTION_DAYS=30
STOCK_GROUPS_REMOTE_URL=
ENABLE_SCHEDULED_GROUP_SYNC=false
```

News API bersifat opsional. Tanpa key, sistem tetap berjalan dan menyebutkan keterbatasan berita.
Aksi korporasi/dividen dari Yahoo Finance digunakan jika tersedia.

Endpoint operasional:

- `/health`: liveness proses.
- `/ready`: kesiapan database dan scan worker.
- `/metrics`: metrik Prometheus, gunakan header `X-Metrics-Key`.
- `/groups`: daftar grup aktif.
- `/admin/groups/sync`: sinkronisasi grup dari `STOCK_GROUPS_REMOTE_URL`.

Validasi atau sinkronisasi grup secara manual:

```bash
venv/bin/python scripts/manage.py validate-groups
venv/bin/python scripts/manage.py sync-groups
```

### Telegram Webhook

Polling cocok untuk satu instance. Untuk HTTPS dan beberapa replica, gunakan mode webhook:

```dotenv
TELEGRAM_MODE=webhook
TELEGRAM_WEBHOOK_BASE_URL=https://stockbot.example.com
TELEGRAM_WEBHOOK_SECRET=secret-random-kuat
```

Pasang contoh `deploy/nginx-ai-stock-analyzer.conf`, arahkan DNS, lalu aktifkan HTTPS menggunakan
Certbot. Persistent scan worker memakai klaim job atomik agar beberapa replica tidak memproses job
yang sama.

### Backup dan Health Check

Siapkan direktori backup:

```bash
sudo mkdir -p /var/backups/ai-stock-analyzer-bot
sudo chown stockbot:stockbot /var/backups/ai-stock-analyzer-bot
sudo cp deploy/ai-stock-analyzer-backup.* /etc/systemd/system/
sudo cp deploy/ai-stock-analyzer-healthcheck.* /etc/systemd/system/
sudo cp deploy/ai-stock-analyzer-restart.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-stock-analyzer-backup.timer
sudo systemctl enable --now ai-stock-analyzer-healthcheck.timer
```

Uji backup dan smoke test:

```bash
sudo systemctl start ai-stock-analyzer-backup.service
sudo -u stockbot venv/bin/python scripts/smoke_test.py
sudo -u stockbot venv/bin/python scripts/smoke_test.py --with-ai
```

Opsi `--with-ai` melakukan satu request AI yang mungkin dikenakan biaya.

Restore salah satu backup:

```bash
gunzip -c /var/backups/ai-stock-analyzer-bot/stockbot-TIMESTAMP.sql.gz | \
  mysql -u stockbot -p stockbot
```

## Upgrade VPS Tanpa Menghapus Data

```bash
cd /var/www/ai-stock-analyzer-bot
sudo systemctl stop ai-stock-analyzer-bot
sudo -u stockbot git pull
sudo -u stockbot venv/bin/pip install -r requirements.txt
sudo -u stockbot venv/bin/alembic upgrade head
sudo cp deploy/ai-stock-analyzer-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start ai-stock-analyzer-bot
curl --fail http://127.0.0.1:8000/ready
```

Alembic menambahkan tabel/kolom baru tanpa menghapus analisa, watchlist, atau hasil scan lama.

## Troubleshooting MySQL Ubuntu

Jika startup gagal dengan pesan `Access denied for user 'root'@'localhost'`, aplikasi masih
menggunakan akun MySQL `root`. Pada Ubuntu, akun tersebut biasanya memakai autentikasi socket dan
tidak dapat dipakai oleh PyMySQL. Buat akun aplikasi khusus:

```bash
DB_PASSWORD="$(openssl rand -hex 24)"
echo "Simpan password database ini: $DB_PASSWORD"
sudo mysql --execute="
CREATE DATABASE IF NOT EXISTS stockbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'stockbot'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER 'stockbot'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON stockbot.* TO 'stockbot'@'localhost';
FLUSH PRIVILEGES;"
```

Ubah `.env` agar memakai user tersebut dan matikan debug untuk produksi:

```dotenv
APP_ENV=production
APP_DEBUG=false
ENABLE_API_DOCS=false
DATABASE_URL=mysql+pymysql://stockbot:PASSWORD_DARI_PERINTAH_DI_ATAS@localhost:3306/stockbot?charset=utf8mb4
```

Uji kredensial sebelum menjalankan aplikasi:

```bash
mysql -u stockbot -p -e "SELECT 1;" stockbot
sudo -u stockbot venv/bin/python -c "from app.database import engine; c=engine.connect(); print('Database OK'); c.close()"
```

## Disclaimer

Seluruh hasil hanya untuk edukasi dan referensi tambahan. Aplikasi tidak memberikan kepastian
profit, tidak menggantikan riset mandiri, dan bukan ajakan membeli atau menjual efek.
