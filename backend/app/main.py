"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.logging import RequestLoggingMiddleware
from app.routers.chat import router as chat_router

app = FastAPI(
    title="AI Persona API",
    description="Yashraj Kupekar's AI representative",
    version="1.0.0",
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# --- Routers ---
app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
