import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import router
from app.bot.telegram_bot import build_telegram_application
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.exceptions import AppError
from app.scheduler import build_scheduler
from app.services.group_service import GroupService
from app.utils.logger import configure_logging

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        GroupService().seed_database(db)

    scheduler = build_scheduler()
    scheduler.start()
    telegram_app = None
    if settings.telegram_bot_token:
        telegram_app = build_telegram_application(settings.telegram_bot_token)
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot polling started")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN is empty; Telegram bot is disabled")

    yield

    if telegram_app:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
    scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, debug=settings.app_debug, lifespan=lifespan)
app.include_router(router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Terjadi kesalahan internal. Coba lagi nanti."},
    )
