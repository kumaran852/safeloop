from contextlib import asynccontextmanager
#Set-executionPolicy -Scope Process Bypass in cd root folder
#.\scripts\setup_windows.ps1
#.scripts\start_windows.ps1
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import models  # noqa: F401  (register tables)
from .api import admin, alerts, analytics, cases, reports, wards, workers
from .config import AUTO_SEED, CORS_ORIGINS, MAX_BODY_BYTES
from .database import Base, SessionLocal, engine
from .seed import seed_demo, seed_reference
from .services.intervention_service import DomainError


@asynccontextmanager
async def lifespan(_app):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_reference(db)
        if AUTO_SEED:
            seed_demo(db)
        db.commit()
    yield


app = FastAPI(title="SAFELOOP API", version="1.0.0", lifespan=lifespan,
              description="Worker signal to verified safety action. Decision-support prototype; not a medical or injury-prediction system.")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type"])


@app.middleware("http")
async def limit_body(request: Request, call_next):
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "Request too large"}, status_code=413)
    return await call_next(request)


@app.exception_handler(DomainError)
async def domain_error(_req, exc: DomainError):
    return JSONResponse({"detail": exc.extra or exc.message}, status_code=exc.status_code)


for r in (admin.router, workers.router, wards.router, reports.router, alerts.router, cases.router, analytics.router):
    app.include_router(r, prefix="/api")
