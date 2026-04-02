"""
PCForge AI — FastAPI Application Entry Point
Production-ready configuration with CORS, lifespan, and structured logging.
"""
from __future__ import annotations
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.routes.analyze import router as analyze_router
from backend.routes.export import router as export_router

# ─── Logging Setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pcforge")


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("🔥 PCForge AI v2 — Starting up...")
    logger.info("=" * 60)

    from backend.data.catalogue import master_catalogue

    raw_dir = Path(__file__).parent.parent / "data" / "raw"
    dataset_path = raw_dir / "pc_parts.json"
    if not dataset_path.exists():
        dataset_path = raw_dir / "pc_parts.sample.json"
        if dataset_path.exists():
            logger.warning("⚠️ Using PLACEHOLDER dataset")

    result = master_catalogue.load(dataset_path)
    if result.success:
        logger.info("✅ Master Catalogue loaded")
    else:
        logger.warning("⚠️ Catalogue fallback")

    from backend.services.prediction_service import prediction_service
    if prediction_service._model_loaded:
        logger.info("✅ ML model loaded")
    else:
        logger.warning("⚠️ ML fallback")

    from backend.data import _get_rules
    rules = _get_rules()
    logger.info("✅ Compatibility rules loaded")

    logger.info("✅ PCForge AI ready")
    yield

    logger.info("👋 Shutting down...")


# ─── App Factory ─────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="PCForge AI",
        description="AI PC builder",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 🔥 FINAL CORS FIX (WORKS WITH YOUR VERCEL FRONTEND)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://pc-forge-ai.vercel.app",  # ✅ your real frontend
            "http://localhost:3000"           # optional local testing
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    # 🔥 API ROUTES
    app.include_router(analyze_router, prefix="/api/v1")
    app.include_router(export_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    @app.get("/")
    async def root():
        return {"service": "PCForge AI"}

    return app


app = create_app()


# ─── Dev Runner ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )