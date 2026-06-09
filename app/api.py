import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from telegram import Update

from app.bot import runtime as bot_runtime
from app.config import get_settings
from app.database import get_db
from app.models.analysis import Analysis
from app.models.user import User
from app.models.watchlist import Watchlist
from app.schemas import AnalysisResponse, AnalyzeRequest, ScanRequest, StockResponse
from app.services.analysis_service import AnalysisService
from app.services.group_service import GroupService
from app.services.scan_job_service import scan_job_service
from app.services.stock_data_service import StockDataService
from app.services.user_service import UserService

router = APIRouter()
settings = get_settings()
analysis_service = AnalysisService()
stock_data_service = StockDataService()
group_service = GroupService()


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_access_key and (
        not x_api_key or not secrets.compare_digest(x_api_key, settings.api_access_key)
    ):
        raise HTTPException(status_code=401, detail="API key tidak valid.")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database belum siap.") from exc
    if not scan_job_service.workers:
        raise HTTPException(status_code=503, detail="Scan worker belum siap.")
    return {
        "status": "ready",
        "database": "ok",
        "scan_workers": len(scan_job_service.workers),
        "configured_ai_providers": settings.configured_ai_providers,
    }


@router.get("/metrics")
def metrics(x_metrics_key: str | None = Header(default=None)) -> Response:
    if settings.metrics_access_key and (
        not x_metrics_key or not secrets.compare_digest(x_metrics_key, settings.metrics_access_key)
    ):
        raise HTTPException(status_code=401, detail="Metrics key tidak valid.")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/stocks/{code}", response_model=StockResponse, dependencies=[Depends(require_api_key)])
async def get_stock(code: str) -> StockResponse:
    data = await stock_data_service.get_stock_data(
        code,
        group_service.find_groups_for_stock(code.upper()),
    )
    return StockResponse(data=data)


@router.post("/analyze", response_model=AnalysisResponse, dependencies=[Depends(require_api_key)])
async def analyze(request: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalysisResponse:
    user = UserService.get_or_create(db, request.telegram_id) if request.telegram_id else None
    result = await analysis_service.analyze_stock(db, request.code, user.id if user else None)
    return AnalysisResponse(
        stock_code=request.code,
        provider=result["provider"],
        final_signal=result["final_signal"],
        confidence_level=result["confidence_level"],
        result=result["text"],
        structured_result=result["structured"],
        provider_errors=result.get("provider_errors", {}),
    )


@router.post(
    "/scan",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_api_key)],
)
async def scan(request: ScanRequest, db: Session = Depends(get_db)) -> dict:
    user = UserService.get_or_create(db, request.telegram_id) if request.telegram_id else None
    job = scan_job_service.submit(
        db,
        request.group_name,
        user.id if user else None,
        request.limit,
    )
    return scan_job_service.serialize(job)


@router.get("/scan/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def scan_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    return scan_job_service.serialize(scan_job_service.get(db, job_id))


@router.get("/history/{telegram_id}", dependencies=[Depends(require_api_key)])
def history(telegram_id: int, db: Session = Depends(get_db)) -> list[dict]:
    user = db.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        return []
    rows = db.scalars(
        select(Analysis)
        .where(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .limit(50)
    ).all()
    return [
        {
            "id": row.id,
            "stock_code": row.stock_code,
            "provider": row.provider,
            "final_signal": row.final_signal,
            "confidence_level": row.confidence_level,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/watchlist/{telegram_id}", dependencies=[Depends(require_api_key)])
def watchlist(telegram_id: int, db: Session = Depends(get_db)) -> list[str]:
    user = db.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        return []
    return list(
        db.scalars(
            select(Watchlist.stock_code)
            .where(Watchlist.user_id == user.id)
            .order_by(Watchlist.stock_code)
        ).all()
    )


@router.get("/groups", dependencies=[Depends(require_api_key)])
def groups() -> dict[str, dict]:
    return group_service.load_groups()


@router.post("/admin/groups/sync", dependencies=[Depends(require_api_key)])
async def sync_groups() -> dict[str, str]:
    if not await group_service.sync_remote_groups():
        raise HTTPException(status_code=400, detail="STOCK_GROUPS_REMOTE_URL belum dikonfigurasi.")
    return {"status": "ok"}


@router.post("/telegram/webhook", include_in_schema=False)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    if settings.telegram_mode != "webhook" or not bot_runtime.telegram_application:
        raise HTTPException(status_code=404, detail="Webhook Telegram tidak aktif.")
    if (
        not x_telegram_bot_api_secret_token
        or not settings.telegram_webhook_secret
        or not secrets.compare_digest(
            x_telegram_bot_api_secret_token,
            settings.telegram_webhook_secret,
        )
    ):
        raise HTTPException(status_code=401, detail="Secret webhook Telegram tidak valid.")
    update = Update.de_json(await request.json(), bot_runtime.telegram_application.bot)
    await bot_runtime.telegram_application.process_update(update)
    return {"ok": True}
