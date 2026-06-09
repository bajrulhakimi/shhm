import gzip
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    url = make_url(settings.database_url)
    if not url.drivername.startswith("mysql"):
        raise SystemExit("Backup script hanya mendukung MySQL.")
    backup_dir = Path(os.getenv("BACKUP_DIR", "/var/backups/ai-stock-analyzer-bot"))
    retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "14"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = backup_dir / f"stockbot-{datetime.now():%Y%m%d-%H%M%S}.sql.gz"
    command = [
        "mysqldump",
        "--single-transaction",
        "--quick",
        "--lock-tables=false",
        "-h",
        url.host or "localhost",
        "-P",
        str(url.port or 3306),
        "-u",
        url.username or "stockbot",
        url.database or "stockbot",
    ]
    env = {**os.environ, "MYSQL_PWD": url.password or ""}
    with gzip.open(destination, "wb") as output:
        subprocess.run(command, stdout=output, stderr=subprocess.PIPE, env=env, check=True)
    cutoff = datetime.now() - timedelta(days=retention_days)
    for backup in backup_dir.glob("stockbot-*.sql.gz"):
        if datetime.fromtimestamp(backup.stat().st_mtime) < cutoff:
            backup.unlink()
    print(destination)


if __name__ == "__main__":
    main()
