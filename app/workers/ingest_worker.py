from __future__ import annotations

from app.logging import get_logger
from app.services.ingestion_service import IngestionService


logger = get_logger(__name__)


class IngestWorker:
    def __init__(self, *, worker_id: str, ingestion_service: IngestionService) -> None:
        self.worker_id = worker_id
        self.ingestion_service = ingestion_service

    def run_once(self) -> bool:
        processed = self.ingestion_service.process_pending_job(self.worker_id)
        if processed:
            logger.info("processed ingest job", extra={"worker_id": self.worker_id})
        return processed

