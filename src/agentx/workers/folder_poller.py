import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path

from agentx.api.ws_manager import ws_manager
from agentx.config import settings
from agentx.db.engine import SessionLocal
from agentx.workers.pipeline_runner import PipelineRunner

logger = logging.getLogger(__name__)

EXTENSION_SOURCE_MAP = {
    ".pdf": "pdf",
    ".json": "api",
    ".xlsx": "excel",
    ".xls": "excel",
    ".swift": "swift",
    ".mt": "swift",
    ".eml": "email",
    ".msg": "email",
}


def resolve_source_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return EXTENSION_SOURCE_MAP.get(ext, "api")


def _resolve_folder(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return settings.project_root / path


class FolderPoller:
    def __init__(self, graph) -> None:
        self.graph = graph
        self._task: asyncio.Task | None = None
        self._processing: set[str] = set()

    @property
    def watch_folder(self) -> Path:
        return _resolve_folder(settings.ingest_watch_folder)

    @property
    def success_folder(self) -> Path:
        return _resolve_folder(settings.ingest_success_folder)

    @property
    def failed_folder(self) -> Path:
        return _resolve_folder(settings.ingest_failed_folder)

    @property
    def review_folder(self) -> Path:
        return _resolve_folder(settings.ingest_review_folder)

    def _ensure_dirs(self) -> None:
        for folder in (self.watch_folder, self.success_folder, self.failed_folder, self.review_folder):
            folder.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        if not settings.ingest_poll_enabled:
            logger.info("Folder ingest poller is disabled")
            return

        self._ensure_dirs()
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "Folder ingest poller started: watch=%s interval=%ss",
            self.watch_folder,
            settings.ingest_poll_interval_seconds,
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("Folder ingest poller stopped")

    async def _loop(self) -> None:
        while True:
            try:
                await self._poll_once()
            except Exception:
                logger.exception("Folder ingest poll cycle failed")
            await asyncio.sleep(settings.ingest_poll_interval_seconds)

    async def _poll_once(self) -> None:
        if not self.watch_folder.exists():
            self._ensure_dirs()
            return

        for file_path in sorted(self.watch_folder.iterdir()):
            if not file_path.is_file():
                continue
            if file_path.name.startswith("."):
                continue
            if file_path.name in self._processing:
                continue

            self._processing.add(file_path.name)
            try:
                await self._process_file(file_path)
            finally:
                self._processing.discard(file_path.name)

    async def _process_file(self, file_path: Path) -> None:
        if not file_path.exists():
            return

        raw = file_path.read_bytes()
        source_type = resolve_source_type(file_path.name)
        logger.info(
            "Processing file: %s (source_type=%s, size=%d bytes)",
            file_path.name,
            source_type,
            len(raw),
        )

        async with SessionLocal() as session:
            runner = PipelineRunner(self.graph, session)
            result = await runner.run(
                raw, source_type, file_path.name, broadcast=ws_manager.broadcast,
            )
            await session.commit()

        destination = self._destination_for_result(result)
        self._move_file(file_path, destination)
        logger.info(
            "File processed: name=%s instruction_id=%s status=%s needs_human_review=%s moved_to=%s",
            file_path.name,
            result.get("instruction_id"),
            result.get("status"),
            result.get("needs_human_review"),
            destination.name,
        )

    def _destination_for_result(self, result: dict) -> Path:
        if not result.get("success"):
            return self.failed_folder
        if result.get("needs_human_review"):
            return self.review_folder
        return self.success_folder

    def _move_file(self, file_path: Path, destination_folder: Path) -> None:
        destination_folder.mkdir(parents=True, exist_ok=True)
        target = destination_folder / file_path.name
        if target.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = destination_folder / f"{file_path.stem}_{stamp}{file_path.suffix}"
        shutil.move(str(file_path), str(target))
