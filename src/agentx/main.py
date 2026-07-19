import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentx.api.routes import router
from agentx.config import settings
from agentx.db.engine import SessionLocal, init_db
from agentx.db.seed import clear_database, seed_database
from agentx.layers.orchestrator.graph import build_graph
from agentx.workers.folder_poller import FolderPoller

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_poller: FolderPoller | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _poller
    await init_db()
    logger.info("Starting %s (debug=%s)", settings.app_name, settings.debug)
    async with SessionLocal() as session:
        await clear_database(session)
        await seed_database(session)
        logger.info("Database seeded from seed/demo_data.json")

    _poller = FolderPoller(build_graph())
    await _poller.start()
    logger.info("Application startup complete")
    yield
    logger.info("Shutting down application")
    await _poller.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
