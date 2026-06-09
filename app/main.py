import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import router
from app.bot.runtime import set_telegram_application
from app.bot.telegram_bot import build_telegram_application
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.exceptions import AppError
from app.monitoring import MetricsMiddleware
from app.scheduler import build_scheduler
from app.services.group_service import GroupService
from app.services.scan_job_service import scan_job_service
from app.utils.logger import configure_logging

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.app_env == "production" and not settings.api_access_key:
        logger.warning("API_ACCESS_KEY is empty; protected REST endpoints are publicly accessible")
    if settings.app_env == "production" and not settings.metrics_access_key:
        logger.warning("METRICS_ACCESS_KEY is empty; /metrics is publicly accessible")
    with SessionLocal() as db:
        GroupService().seed_database(db)

    scheduler = build_scheduler()
    scheduler.start()
    await scan_job_service.start()
    telegram_app = None
    if settings.telegram_bot_token:
        telegram_app = build_telegram_application(settings.telegram_bot_token)
        await telegram_app.initialize()
        await telegram_app.start()
        set_telegram_application(telegram_app)
        if settings.telegram_mode == "webhook":
            if not settings.telegram_webhook_base_url or not settings.telegram_webhook_secret:
                raise RuntimeError("Telegram webhook URL dan secret wajib diisi pada mode webhook.")
            webhook_url = f"{settings.telegram_webhook_base_url.rstrip('/')}/telegram/webhook"
            await telegram_app.bot.set_webhook(
                webhook_url,
                secret_token=settings.telegram_webhook_secret,
                drop_pending_updates=True,
            )
            logger.info("Telegram webhook configured")
        else:
            await telegram_app.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram bot polling started")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN is empty; Telegram bot is disabled")

    yield

    if telegram_app:
        if settings.telegram_mode == "polling":
            await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
        set_telegram_application(None)
    await scan_job_service.stop()
    scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)
app.add_middleware(MetricsMiddleware)
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
