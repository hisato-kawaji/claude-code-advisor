from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import stats, analysis

app = FastAPI(
    title="Claude Code Analytics API",
    description="API for analyzing Claude Code usage and providing improvement suggestions",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3332", "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターを登録
app.include_router(stats.router)
app.include_router(analysis.router)


@app.get("/")
async def root():
    return {
        "message": "Claude Code Analytics API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
