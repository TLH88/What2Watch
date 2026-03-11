from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import discover, health, integrations, titles, users

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
