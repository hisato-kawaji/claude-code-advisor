from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api import stats, analysis
from app.services.data_collector import ClaudeDataCollector
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーション起動時と終了時の処理"""
    # 起動時：DBの初期化と同期
    print("Initializing database...")
    settings = get_settings()
    collector = ClaudeDataCollector(settings.claude_data_path, settings.database_path)

    # DBが空の場合のみ同期を実行
    if collector.db.get_total_entries_count() == 0:
        print("Database is empty. Starting initial sync...")
        result = collector.sync_to_database()
        print(f"Initial sync completed: {result}")
    else:
        print(f"Database already contains {collector.db.get_total_entries_count()} entries")

    yield
    # 終了時の処理（必要に応じて）
    print("Shutting down...")


app = FastAPI(
    title="Claude Code Analytics API",
    description="API for analyzing Claude Code usage and providing improvement suggestions",
    version="1.0.0",
    lifespan=lifespan
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
