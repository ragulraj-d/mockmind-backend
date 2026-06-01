import asyncio
import os
from contextlib import asynccontextmanager

import firebase_admin
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()

from routes import interview, history

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PING_INTERVAL = 10 * 60  # 10 minutes

# ── Rate limiter (IP-based outer layer) ──────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])


async def _keep_alive():
    await asyncio.sleep(30)
    url = f"{RENDER_URL}/health" if RENDER_URL else None
    if not url:
        print("RENDER_EXTERNAL_URL not set — keep-alive disabled")
        return
    print(f"Keep-alive → pinging {url} every {PING_INTERVAL // 60} min")
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            try:
                r = await client.get(url)
                print(f"Keep-alive: {r.status_code}")
            except Exception as e:
                print(f"Keep-alive failed: {e}")
            await asyncio.sleep(PING_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Groq key check ────────────────────────────────────────────────────────
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        print(f"GROQ_API_KEY loaded (prefix: {groq_key[:8]}...)")
    else:
        print("WARNING: GROQ_API_KEY not set")

    # ── Firebase init ─────────────────────────────────────────────────────────
    if not firebase_admin._apps:
        sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-service-account.json")
        if sa_path and os.path.exists(sa_path):
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized with service account")
        else:
            # Project-ID-only init: enables token verification without a service account
            project_id = os.getenv("FIREBASE_PROJECT_ID", "mockmindai")
            firebase_admin.initialize_app(options={"projectId": project_id})
            print(f"Firebase initialized (project-id only: {project_id}) — Firestore writes disabled")

    # ── Keep-alive background task ────────────────────────────────────────────
    task = asyncio.create_task(_keep_alive())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="MockMind API",
    description="AI-powered mock interview backend — Groq (Llama 3.3 70B)",
    version="2.0.0",
    lifespan=lifespan,
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview.router, prefix="/api", tags=["Interview"])
app.include_router(history.router, prefix="/api", tags=["History"])


@app.get("/")
async def root():
    return {"message": "MockMind API is running", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}
