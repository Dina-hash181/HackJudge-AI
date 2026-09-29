import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.database import init_db
from src.seed_data import seed_database
from src.routes.auth_routes import router as auth_router
from src.routes.participant_routes import router as participant_router
from src.routes.judge_routes import router as judge_router
from src.routes.admin_routes import router as admin_router
from src.routes.public_routes import router as public_router
from src.routes.ai_routes import router as ai_router
from src.config import BASE_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and seed data automatically on startup
    init_db()
    seed_database(force=False)
    yield

app = FastAPI(
    title="HackJudge AI · Autonomous Hackathon Management & Judging Platform",
    description="The self-hosted hackathon platform that judges you. Complete lifecycle management with normalized cross-judge evaluation.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Register API Routers
app.include_router(auth_router)
app.include_router(participant_router)
app.include_router(judge_router)
app.include_router(admin_router)
app.include_router(public_router)
app.include_router(ai_router)

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    """Serves the main single-page application dashboard."""
    template_path = Path(__file__).resolve().parent / "templates" / "index.html"
    if template_path.exists():
        content = template_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content, status_code=200)
    return HTMLResponse("<h1>DOGFOOD 2026 Portal Running</h1>", status_code=200)

if __name__ == "__main__":
    import uvicorn
    from src.config import HOST, PORT
    uvicorn.run("src.main:app", host=HOST, port=PORT, reload=False)
