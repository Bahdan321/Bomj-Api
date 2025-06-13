from __future__ import annotations

from contextlib import asynccontextmanager
import os

from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.packs import router as packs_router
from app.services import supabase_client

# Load .env in local/dev environments
if os.getenv("ENV", "dev") == "dev":
    load_dotenv(override=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Приложение запускается...")
    yield
    print("Приложение завершает работу...")
    await supabase_client.dispose()
    
app = FastAPI(
    lifespan=lifespan,
)

app = FastAPI(
    title="Bomj API",
    version="0.1.0",
    description="Upload assets to Cloudflare R2 and register sound packs in Supabase (PostgreSQL).",
)

# Register routers
app.include_router(packs_router)


@app.get("/", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
