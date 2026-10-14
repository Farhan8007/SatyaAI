import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import database
from app.routers import auth, papers, audit, alerts, dashboard, reports, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.connect()
    yield
    database.close()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def catch_unhandled_errors(request: Request, call_next):
    # IMPORTANT: Starlette's add_middleware() prepends to the middleware
    # list, so whichever middleware is registered LAST ends up OUTERMOST.
    # This must be registered BEFORE app.add_middleware(CORSMiddleware)
    # below so that it ends up INSIDE (closer to the routes than) CORS.
    # If it were outside CORS, the JSONResponse built here would bypass
    # CORSMiddleware's header injection entirely, and the browser would
    # still report a misleading "blocked by CORS policy" error instead of
    # the actual message below.
    try:
        return await call_next(request)
    except Exception:
        print("=" * 70)
        print(f"UNHANDLED ERROR on {request.method} {request.url.path}")
        traceback.print_exc()
        print("=" * 70)
        return JSONResponse(
            status_code=500,
            content={
                "detail": (
                    "Something went wrong on the server. This is very often "
                    "MongoDB not running -- check that it's started, then "
                    "check the backend terminal for the full error just "
                    "printed above."
                )
            },
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(papers.router)
app.include_router(audit.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(reports.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": settings.app_name}
