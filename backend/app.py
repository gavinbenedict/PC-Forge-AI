"""
PCForge AI — FastAPI Application Entry Point
Production-ready configuration with CORS, lifespan, and structured logging.
"""
from __future__ import annotations
import logging
import os
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
    """
    Startup: load master catalogue, ML model, and validate compatibility rules.
    Shutdown: no-op (stateless).
    """
    logger.info("=" * 60)
    logger.info("🔥 PCForge AI v2 — Starting up...")
    logger.info("=" * 60)

    # ── 1. Master Catalogue ──────────────────────────────────────────────────
    from backend.data.catalogue import master_catalogue

    # Resolve dataset path: prefer pc_parts.json, fall back to .sample.json
    raw_dir = Path(__file__).parent.parent / "data" / "raw"
    dataset_path = raw_dir / "pc_parts.json"
    if not dataset_path.exists():
        dataset_path = raw_dir / "pc_parts.sample.json"
        if dataset_path.exists():
            logger.warning("⚠️  Using PLACEHOLDER dataset (pc_parts.sample.json). "
                           "Drop your real dataset at data/raw/pc_parts.json to activate it.")

    result = master_catalogue.load(dataset_path)
    if result.success:
        logger.info(
            "✅ Master Catalogue loaded: %d components %s",
            result.component_count,
            {k: v for k, v in result.category_counts.items()},
        )
    else:
        logger.warning(
            "⚠️  Catalogue not loaded (%s). Services will use built-in fallback data.",
            result.errors[0] if result.errors else "unknown reason",
        )

    # ── 2. ML Price Prediction Model ─────────────────────────────────────────
    from backend.services.prediction_service import prediction_service
    if prediction_service._model_loaded:
        logger.info("✅ ML price prediction model loaded")
    else:
        logger.warning("⚠️  ML model not found — heuristic fallback active. "
                       "Run: python -m backend.models.train_model")

    # ── 3. Compatibility Rules (JSON fallback still needed) ───────────────────
    from backend.data import _get_rules
    rules = _get_rules()
    logger.info("✅ Compatibility rules (fallback): %d CPU socket mappings, %d GPU TDP entries",
                len(rules.get("cpu_socket_map", {})),
                len(rules.get("gpu_tdp_watts", {})))

    logger.info("✅ PCForge AI v2 ready — http://localhost:8000")
    logger.info("📖 API docs: http://localhost:8000/docs")
    yield

    logger.info("👋 PCForge AI shutting down...")


# ─── App Factory ─────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="PCForge AI",
        description=(
            "Intelligent PC Build Pricing and Recommendation Engine. "
            "Validates compatibility, recommends missing components, estimates prices, "
            "and exports full results as CSV or Excel."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    cors_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler ──────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
            },
        )

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(analyze_router, prefix="/api/v1")
    app.include_router(export_router, prefix="/api/v1")

    # ── Health check ──────────────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        from backend.services.prediction_service import prediction_service
        from backend.data.catalogue import master_catalogue
        return {
            "status": "healthy",
            "service": "PCForge AI",
            "version": "2.0.0",
            "ml_model_loaded": prediction_service._model_loaded,
            "catalogue": master_catalogue.stats(),
        }

    @app.get("/", tags=["System"])
    async def root():
        return {
            "service": "PCForge AI",
            "version": "1.0.0",
            "endpoints": {
                "analyze": "POST /api/v1/analyze-build",
                "export_csv": "POST /api/v1/export/csv",
                "export_excel": "POST /api/v1/export/excel",
                "health": "GET /health",
                "docs": "GET /docs",
            }
        }

    return app


app = create_app()


# ─── Dev Runner ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
        log_level="info",
    )
