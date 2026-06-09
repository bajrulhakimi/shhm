import logging

from sqlalchemy import delete, select
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import MAIN_KEYBOARD
from app.config import get_settings
from app.database import SessionLocal
from app.exceptions import AppError
from app.models.analysis import Analysis
from app.models.watchlist import Watchlist
from app.services.analysis_service import AnalysisService
from app.services.scan_job_service import scan_job_service
from app.services.user_service import UserService
from app.utils.formatter import DISCLAIMER, split_telegram_message
from app.utils.validators import normalize_stock_code

logger = logging.getLogger(__name__)
settings = get_settings()
analysis_service = AnalysisService()

HELP_TEXT = """Perintah AI Stock Analyzer:
/analyze KODE - analisa satu saham
/scan - scan sampel IHSG
/scan_lq45, /scan_idx30, /scan_idx80
/scan_jii, /scan_dividend, /scan_esg, /scan_all
/scan_status JOB_ID - lihat progress atau hasil scan
/watchlist - lihat watchlist
/addwatch KODE - tambah watchlist
/removewatch KODE - hapus watchlist
/history - riwayat analisa
/settings - konfigurasi aktif

Contoh: /analyze BBCA

""" + DISCLAIMER

SCAN_COMMANDS = {
    "scan": "IHSG",
    "scan_lq45": "LQ45",
    "scan_idx30": "IDX30",
    "scan_idx80": "IDX80",
    "scan_jii": "JII",
    "scan_dividend": "DIVIDEND",
    "scan_esg": "ESG",
    "scan_all": "ALL",
}


def _user_from_update(db, update: Update):
    telegram_user = update.effective_user
    return UserService.get_or_create(
        db,
        telegram_user.id,
        telegram_user.username,
        telegram_user.first_name,
        telegram_user.last_name,
    )


async def _reply_long(update: Update, text: str) -> None:
    for chunk in split_telegram_message(text):
        await update.effective_message.reply_text(chunk)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with SessionLocal() as db:
        _user_from_update(db, update)
    await update.effective_message.reply_text(
        "Selamat datang di AI Stock Analyzer Bot.\n\n" + HELP_TEXT,
        reply_markup=MAIN_KEYBOARD,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(HELP_TEXT, reply_markup=MAIN_KEYBOARD)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Format: /analyze KODE\nContoh: /analyze BBCA")
        return
    code = context.args[0]
    status = await update.effective_message.reply_text(
        f"Mengambil data dan menganalisa {code.upper()}..."
    )
    try:
        with SessionLocal() as db:
            user = _user_from_update(db, update)
            result = await analysis_service.analyze_stock(db, code, user.id)
        await status.edit_text(f"Analisa {normalize_stock_code(code)} selesai.")
        await _reply_long(update, result["text"])
    except AppError as exc:
        await status.edit_text(str(exc))
    except Exception:
        logger.exception("Unexpected Telegram analysis error")
        await status.edit_text(
            f"Maaf, data saham {code.upper()} belum berhasil dianalisa. Coba lagi nanti."
        )


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command = update.effective_message.text.split()[0].lstrip("/").split("@")[0]
    group = SCAN_COMMANDS.get(command, "IHSG")
    status = await update.effective_message.reply_text(
        f"Memulai scan {group}. Proses ini dapat memerlukan beberapa menit..."
    )
    try:
        with SessionLocal() as db:
            user = _user_from_update(db, update)
            job = scan_job_service.submit(db, group, user.id)
            job_id = job.id
        await status.edit_text(f"Scan {group} masuk antrean. Job ID: {job_id}")
        job = await scan_job_service.wait(job_id)
        if job.status == "failed":
            raise AppError(job.error_message or "Scan gagal dijalankan.")
        result = job.result or {"results": [], "errors": [], "formatted": "Hasil scan kosong."}
        success_count = len(result["results"])
        error_count = len(result["errors"])
        await status.edit_text(
            f"Scan {group} selesai: {success_count} berhasil, {error_count} gagal."
        )
        await _reply_long(update, result["formatted"])
    except AppError as exc:
        await status.edit_text(str(exc))
    except Exception:
        logger.exception("Unexpected Telegram scan error")
        await status.edit_text("Maaf, scan belum berhasil dijalankan. Coba lagi nanti.")


async def scan_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Format: /scan_status JOB_ID")
        return
    try:
        with SessionLocal() as db:
            user = _user_from_update(db, update)
            job = scan_job_service.get(db, context.args[0])
            if job.user_id and job.user_id != user.id:
                raise AppError("Job scan tidak ditemukan.")
            payload = scan_job_service.serialize(job)
        if payload["status"] == "completed" and payload["result"]:
            await _reply_long(update, payload["result"]["formatted"])
            return
        message = (
            f"Job {payload['id']}\n"
            f"Status: {payload['status']}\n"
            f"Progress: {payload['processed_stocks']}/{payload['total_stocks']} "
            f"({payload['progress_percent']}%)"
        )
        if payload["error_message"]:
            message += f"\nError: {payload['error_message']}"
        await update.effective_message.reply_text(message)
    except AppError as exc:
        await update.effective_message.reply_text(str(exc))


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with SessionLocal() as db:
        user = _user_from_update(db, update)
        codes = db.scalars(
            select(Watchlist.stock_code)
            .where(Watchlist.user_id == user.id)
            .order_by(Watchlist.stock_code)
        ).all()
    entries = "\n".join(f"- {code}" for code in codes) if codes else "- Masih kosong"
    text = "Watchlist Anda:\n" + entries
    await update.effective_message.reply_text(text)


async def addwatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Format: /addwatch KODE")
        return
    try:
        code = normalize_stock_code(context.args[0])
        with SessionLocal() as db:
            user = _user_from_update(db, update)
            existing = db.scalar(
                select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.stock_code == code)
            )
            if not existing:
                db.add(Watchlist(user_id=user.id, stock_code=code))
                db.commit()
        await update.effective_message.reply_text(f"{code} ditambahkan ke watchlist.")
    except AppError as exc:
        await update.effective_message.reply_text(str(exc))


async def removewatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Format: /removewatch KODE")
        return
    try:
        code = normalize_stock_code(context.args[0])
        with SessionLocal() as db:
            user = _user_from_update(db, update)
            db.execute(
                delete(Watchlist).where(Watchlist.user_id == user.id, Watchlist.stock_code == code)
            )
            db.commit()
        await update.effective_message.reply_text(f"{code} dihapus dari watchlist.")
    except AppError as exc:
        await update.effective_message.reply_text(str(exc))


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with SessionLocal() as db:
        user = _user_from_update(db, update)
        rows = db.scalars(
            select(Analysis)
            .where(Analysis.user_id == user.id)
            .order_by(Analysis.created_at.desc())
            .limit(10)
        ).all()
    lines = ["10 analisa terbaru:"]
    lines.extend(
        f"- {row.created_at:%d-%m-%Y %H:%M} | {row.stock_code} | {row.final_signal or 'N/A'}"
        for row in rows
    )
    if not rows:
        lines.append("- Belum ada riwayat.")
    await update.effective_message.reply_text("\n".join(lines))


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    providers = ", ".join(settings.configured_ai_providers) or "belum ada"
    await update.effective_message.reply_text(
        "Konfigurasi aktif:\n"
        f"- Provider default: {settings.default_ai_provider}\n"
        f"- Provider tersedia: {providers}\n"
        f"- Multi AI: {'aktif' if settings.enable_multi_ai else 'nonaktif'}\n"
        f"- Batas analisa/hari: {settings.max_analysis_per_day}\n"
        f"- Batas scan/hari: {settings.max_scan_per_day}\n"
        f"- Maksimum saham/scan: {settings.max_scan_stocks}"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Telegram handler error", exc_info=context.error)
