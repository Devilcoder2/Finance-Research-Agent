# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.research import router as research_router

app = FastAPI(
    title="Financial Research Analyst Platform API",
    description="REST and Event Streaming API for the Hierarchical Multi-Agent Analyst Platform",
    version="1.0.0"
)

# CORS middleware to allow connection from standard frontend ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register research API router
app.include_router(research_router, prefix="/api/research", tags=["Research"])

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Financial Research Analyst Platform API is online and healthy."
    }
