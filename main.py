import asyncio
import os
from contextlib import asynccontextmanager

import firebase_admin
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials

load_dotenv()

from routes import interview, history

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PING_INTERVAL = 10 * 60  # 10 minutes


async def _keep_alive():
    """Pings the /health endpoint every 10 min to prevent Render free-tier sleep."""
    await asyncio.sleep(30)  # let server fully start first
    url = f"{RENDER_URL}/health" if RENDER_URL else None
    if not url:
        print("RENDER_EXTERNAL_URL not set — keep-alive disabled")
        return
    print(f"Keep-alive started → pinging {url} every {PING_INTERVAL // 60} min")
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            try:
                r = await client.get(url)
                print(f"Keep-alive ping: {r.status_code}")
            except Exception as e:
                print(f"Keep-alive ping failed: {e}")
            await asyncio.sleep(PING_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Groq key check
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        print(f"GROQ_API_KEY loaded (prefix: {groq_key[:8]}...)")
    else:
        print("WARNING: GROQ_API_KEY not set - AI features will fail")

    # Firebase (optional)
    if not firebase_admin._apps:
        service_account_path = os.getenv(
            "FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-service-account.json"
        )
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized successfully")
        else:
            print("Firebase service account not found - Firestore features disabled")

    # Start keep-alive background task
    task = asyncio.create_task(_keep_alive())

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="MockMind API",
    description="AI-powered mock interview backend powered by Groq (Llama 3.3 70B)",
    version="1.0.0",
    lifespan=lifespan,
)

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
    return {"message": "MockMind API is running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.1"}
