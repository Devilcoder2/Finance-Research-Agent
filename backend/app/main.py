# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

# Centralized logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend.api")

from backend.app.api.research import router as research_router
from backend.app.api.auth import router as auth_router

app = FastAPI(
    title="Financial Research Analyst Platform API",
    description="REST and Event Streaming API for the Hierarchical Multi-Agent Analyst Platform",
    version="1.0.0"
)

# HTTP middleware to log API requests & execution times
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(
            f"Uncaught exception during request {request.method} {request.url.path}: {str(e)}", 
            exc_info=True
        )
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        status_code = response.status_code if response else 500
        logger.info(
            f"Method: {request.method} | Path: {request.url.path} | "
            f"Status: {status_code} | Duration: {duration_ms:.2f}ms"
        )

# CORS middleware to allow connection from standard frontend ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(research_router, prefix="/api/research", tags=["Research"])

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Financial Research Analyst Platform API is online and healthy."
    }
