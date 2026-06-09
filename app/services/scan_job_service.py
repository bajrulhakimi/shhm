import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.exceptions import AppError
from app.models.scan_job import ScanJob
from app.monitoring import SCAN_JOBS
from app.services.scan_service import ScanService

logger = logging.getLogger(__name__)


class ScanJobService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.scan_service = ScanService()
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.workers: list[asyncio.Task] = []

    async def start(self) -> None:
        if self.workers:
            return
        with SessionLocal() as db:
            db.execute(
                update(ScanJob)
                .where(ScanJob.status == "running")
                .values(status="queued", error_message="Job dipulihkan setelah restart aplikasi.")
            )
            db.commit()
            queued_ids = db.scalars(
                select(ScanJob.id).where(ScanJob.status == "queued").order_by(ScanJob.created_at)
            ).all()
        for job_id in queued_ids:
            self.queue.put_nowait(job_id)
        self.workers = [
            asyncio.create_task(self._worker(index), name=f"scan-worker-{index}")
            for index in range(self.settings.scan_worker_count)
        ]
        logger.info("%s scan worker(s) started", len(self.workers))

    async def stop(self) -> None:
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    def submit(
        self,
        db: Session,
        group_name: str,
        user_id: int | None = None,
        limit: int | None = None,
    ) -> ScanJob:
        self.scan_service.ai.ensure_available()
        self.scan_service.usage.check_and_record(db, user_id, "scan")
        codes = self.scan_service.groups.get_codes(group_name)
        effective_limit = min(
            limit or self.settings.max_scan_stocks,
            self.settings.max_scan_stocks,
        )
        job = ScanJob(
            id=str(uuid4()),
            user_id=user_id,
            group_name=group_name.upper(),
            requested_limit=effective_limit,
            total_stocks=min(len(codes), effective_limit),
            status="queued",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        self.queue.put_nowait(job.id)
        return job

    @staticmethod
    def get(db: Session, job_id: str) -> ScanJob:
        job = db.get(ScanJob, job_id)
        if not job:
            raise AppError("Job scan tidak ditemukan.")
        return job

    @staticmethod
    def serialize(job: ScanJob) -> dict[str, Any]:
        return {
            "id": job.id,
            "group_name": job.group_name,
            "status": job.status,
            "total_stocks": job.total_stocks,
            "processed_stocks": job.processed_stocks,
            "progress_percent": (
                round(job.processed_stocks / job.total_stocks * 100, 2)
                if job.total_stocks
                else 0
            ),
            "result": job.result,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        }

    async def wait(self, job_id: str, poll_seconds: float = 1) -> ScanJob:
        while True:
            with SessionLocal() as db:
                job = self.get(db, job_id)
                db.expunge(job)
            if job.status in {"completed", "failed"}:
                return job
            await asyncio.sleep(poll_seconds)

    async def _worker(self, worker_index: int) -> None:
        while True:
            queued_locally = True
            try:
                job_id = await asyncio.wait_for(self.queue.get(), timeout=2)
            except TimeoutError:
                queued_locally = False
                with SessionLocal() as db:
                    job_id = db.scalar(
                        select(ScanJob.id)
                        .where(ScanJob.status == "queued")
                        .order_by(ScanJob.created_at)
                        .limit(1)
                    )
                if not job_id:
                    continue
            try:
                await self._execute(job_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Scan worker %s failed job %s", worker_index, job_id)
            finally:
                if queued_locally:
                    self.queue.task_done()

    async def _execute(self, job_id: str) -> None:
        with SessionLocal() as db:
            claimed = db.execute(
                update(ScanJob)
                .where(ScanJob.id == job_id, ScanJob.status == "queued")
                .values(status="running", started_at=datetime.now(), error_message=None)
            )
            db.commit()
            if claimed.rowcount != 1:
                return
            job = self.get(db, job_id)

            def update_progress(processed: int, total: int) -> None:
                job.processed_stocks = processed
                job.total_stocks = total
                db.commit()

            try:
                result = await self.scan_service.scan_group(
                    db,
                    job.group_name,
                    job.user_id,
                    job.requested_limit,
                    enforce_limit=False,
                    progress_callback=update_progress,
                )
                job.result = result
                job.status = "completed"
                SCAN_JOBS.labels("completed").inc()
            except Exception as exc:
                db.rollback()
                job = self.get(db, job_id)
                job.status = "failed"
                job.error_message = str(exc)[:2000]
                SCAN_JOBS.labels("failed").inc()
            job.finished_at = datetime.now()
            db.commit()


scan_job_service = ScanJobService()
