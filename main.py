from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import firebase_admin
from firebase_admin import credentials
import os
from dotenv import load_dotenv

load_dotenv()

from routes import interview, history


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
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-service-account.json")
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized successfully")
        else:
            print("Firebase service account not found - Firestore features disabled")
    yield


app = FastAPI(
    title="MockMind API",
    description="AI-powered mock interview backend powered by Gemini",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mockmind.web.app",
        "https://mockmind.firebaseapp.com",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost",
    ],
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
