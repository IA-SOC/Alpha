"""Run with: uvicorn app.main:app --host 127.0.0.1 --port 8000."""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes.cases import router
from app.api.routes.chat import router as chat_router
from app.api.routes.investigations import router as investigation_router
from app.core.config import settings
from app.services.case_service import CaseService
from app.services.chat_service import ChatService
from app.services.investigation_service import InvestigationService
from app.storage.case_store import CaseStore


def create_app(*, database_path: Path | None = None) -> FastAPI:
    automatic = os.getenv("SOC_AUTO_INVESTIGATE", "true").lower() == "true"
    store = CaseStore(database_path or settings.case_database_path)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        store.initialize()
        store.recover_jobs()
        worker = (
            asyncio.create_task(application.state.investigation_service.worker())
            if automatic
            else None
        )
        try:
            yield
        finally:
            if worker is not None:
                worker.cancel()
                with suppress(asyncio.CancelledError):
                    await worker

    application = FastAPI(
        title="SOC AI Analyst Sprint 2", version="1.1.0", lifespan=lifespan
    )
    application.state.case_service = CaseService(settings, store)
    application.state.investigation_service = InvestigationService(store)
    application.state.investigation_service.require_gemini = automatic
    application.state.chat_service = ChatService(
        application.state.investigation_service
    )
    register_error_handlers(application)
    application.include_router(chat_router)
    application.include_router(router)
    application.include_router(investigation_router)
    return application


app = create_app()
