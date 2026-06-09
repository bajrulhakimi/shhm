from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.services.scan_job_service import ScanJobService


def test_submit_scan_job(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    service = ScanJobService()
    monkeypatch.setattr(service.scan_service.ai, "ensure_available", lambda: None)

    job = service.submit(session, "LQ45", limit=3)
    serialized = service.serialize(job)

    assert job.status == "queued"
    assert job.total_stocks == 3
    assert serialized["progress_percent"] == 0


async def test_worker_completes_persistent_job(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    service = ScanJobService()
    monkeypatch.setattr("app.services.scan_job_service.SessionLocal", factory)
    monkeypatch.setattr(service.scan_service.ai, "ensure_available", lambda: None)

    async def fake_scan(*args, progress_callback=None, **kwargs):
        progress_callback(1, 1)
        return {"results": [], "errors": [], "formatted": "selesai"}

    monkeypatch.setattr(service.scan_service, "scan_group", fake_scan)
    with factory() as session:
        job = service.submit(session, "LQ45", limit=1)

    await service.start()
    finished = await service.wait(job.id, poll_seconds=0.01)
    await service.stop()

    assert finished.status == "completed"
    assert finished.processed_stocks == 1
    assert finished.result["formatted"] == "selesai"
