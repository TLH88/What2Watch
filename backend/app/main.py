import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routes import admin, discover, health, integrations, recall, reminders, titles, users

logger = logging.getLogger(__name__)

app = FastAPI(
    title="What2Watch",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(titles.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(discover.router, prefix="/api")
app.include_router(recall.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )
