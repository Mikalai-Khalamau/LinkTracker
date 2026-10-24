import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from src.config import settings
from src.logger import get_logger, setup_logger
from src.db.migrations import run_migrations
from src.repositories.factory import create_repositories, close_repositories
from src.routes import api
from src.scheduler.update_checker import run_scheduler
from src.services.notification_service import init_sender, get_sender, shutdown_sender
from src.services.kafka_message_sender import KafkaMessageSender
from src.cache import ValkeyClient
from src.limiter import limiter

scheduler_task: asyncio.Task | None = None
repositories: dict | None = None
cache_client: ValkeyClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger(settings.log_level)
    logger = get_logger()

    logger.info("scrapper_service_starting", port=settings.port)

    logger.info("running_database_migrations")
    run_migrations(settings.db_url)
    logger.info("migrations_completed")

    global repositories
    repositories = await create_repositories(settings)
    logger.info("repositories_created", access_type=repositories["type"])

    app.state.chat_repository = repositories["chat"]
    app.state.link_repository = repositories["link"]

    global cache_client
    if settings.valkey_enabled:
        cache_client = ValkeyClient()
        try:
            await cache_client.connect()
            app.state.cache_client = cache_client
            logger.info("valkey_cache_enabled")
        except Exception as e:
            logger.error("valkey_connection_failed", error=str(e))
            cache_client = None
            app.state.cache_client = None
    else:
        app.state.cache_client = None
        logger.info("valkey_cache_disabled")

    init_sender()
    sender = get_sender()

    if isinstance(sender, KafkaMessageSender):
        await sender.start()
        logger.info("kafka_producer_started_via_lifespan")

    global scheduler_task
    scheduler_task = asyncio.create_task(run_scheduler(repositories["link"], sender))
    logger.info(
        "scheduler_started",
        interval_seconds=settings.check_interval,
        batch_size=settings.batch_size,
    )

    try:
        yield
    finally:
        logger.info("scrapper_service_stopping")

        if scheduler_task and not scheduler_task.done():
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass

        await shutdown_sender()

        if cache_client is not None:
            await cache_client.disconnect()

        if repositories:
            await close_repositories(repositories)

        logger.info("scrapper_service_stopped")


app = FastAPI(
    title="Scrapper API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(api.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
