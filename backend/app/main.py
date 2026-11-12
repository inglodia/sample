from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import auth, chat, dashboard, users

app = FastAPI(title="Portal API")

# Session first, then CORS (last added = outermost; CORS wraps session/cookies).
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="portal_session",
    max_age=14 * 24 * 60 * 60,
    same_site="lax",
    https_only=False,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
