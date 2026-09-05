from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import get_settings
from app.db.session import init_db, init_domain_db
from app.api.webhooks import router as webhooks_router
from app.api.opportunities import router as opportunities_router
from app.api.actions import router as actions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Initialize minimal webhook database schema
    init_db()
    # Initialize domain database schema
    init_domain_db()
    yield


app = FastAPI(
    title=get_settings().APP_NAME,
    version="0.1.0",
    description="RecoverAI Decision and Revenue Recovery Orchestration Backend",
    lifespan=lifespan
)

# Register routers
app.include_router(webhooks_router)
app.include_router(opportunities_router)
app.include_router(actions_router)


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint adhering to 22_API_SPECIFICATION.md."""
    return {
        "status": "healthy",
        "service": get_settings().APP_NAME,
        "version": "0.1.0"
    }
