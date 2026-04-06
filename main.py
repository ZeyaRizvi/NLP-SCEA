from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.complaints_db import init_db

from routes.analyze import router as analyze_router
from routes.root import router as root_router
from routes.complaints import router as complaints_router


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Ensure SQLite schema exists before serving requests.
        init_db()
        yield

    app = FastAPI(title="Smart Electricity Complaint Analyzer", lifespan=lifespan)
    # Fallback: some test/dev environments may not trigger lifespan startup reliably.
    # Creating the schema eagerly keeps the API functional.
    init_db()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(root_router)
    app.include_router(analyze_router)
    app.include_router(complaints_router)
    return app


app = create_app()

