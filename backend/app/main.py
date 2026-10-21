from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import settings
from backend.app.api.v1.router import api_router
from backend.app.database.session import init_db

# Initialize database schema on startup
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="CodeEcho: An AI-Assisted Pattern Recognition System for Detecting Recurring Anti-Patterns in Software Repositories.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

if settings.SERVE_FRONTEND and Path(settings.FRONTEND_DIST_DIR).exists():
    app.mount("/", StaticFiles(directory=settings.FRONTEND_DIST_DIR, html=True), name="static_frontend")
else:
    @app.get("/")
    def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "description": "CodeEcho API Backend",
            "docs": f"{settings.API_V1_STR}/docs",
        }
