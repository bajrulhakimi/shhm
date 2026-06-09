from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.analysis import Analysis
from app.models.user import User
from app.models.watchlist import Watchlist
from app.schemas import AnalysisResponse, AnalyzeRequest, ScanRequest, StockResponse
from app.services.analysis_service import AnalysisService
from app.services.group_service import GroupService
from app.services.scan_service import ScanService
from app.services.stock_data_service import StockDataService
from app.services.user_service import UserService

router = APIRouter()
settings = get_settings()
analysis_service = AnalysisService()
scan_service = ScanService()
stock_data_service = StockDataService()
group_service = GroupService()


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_access_key and x_api_key != settings.api_access_key:
        raise HTTPException(status_code=401, detail="API key tidak valid.")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}


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
        provider_errors=result.get("provider_errors", {}),
    )


@router.post("/scan", dependencies=[Depends(require_api_key)])
async def scan(request: ScanRequest, db: Session = Depends(get_db)) -> dict:
    user = UserService.get_or_create(db, request.telegram_id) if request.telegram_id else None
    return await scan_service.scan_group(
        db,
        request.group_name,
        user.id if user else None,
        request.limit,
    )


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
