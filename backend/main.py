from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine, SessionLocal
from models import AppConfig
from routers import ingest, cleanse, etl, eda, charts, narrative, license, config

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Datalytica API",
    description="Backend API for the Datalytica desktop analytics platform",
    version="1.0.0",
)

# CORS — allow Electron renderer
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# License enforcement middleware
@app.middleware("http")
async def license_check_middleware(request: Request, call_next):
    # Exclude health + license endpoints from check
    open_paths = ("/", "/api/health")
    if request.url.path.startswith("/api/license") or request.url.path in open_paths:
        return await call_next(request)

    from services.license_service import is_admin_mode, validate_key
    if is_admin_mode():
        return await call_next(request)

    db = SessionLocal()
    try:
        config = db.query(AppConfig).filter(AppConfig.key == "LICENSE_KEY").first()
        key = config.value if config else None
    finally:
        db.close()

    if not key:
        return JSONResponse(status_code=403, content={"error": "license_required", "detail": "No license key configured"})

    res = validate_key(key)
    if not res.get("valid"):
        return JSONResponse(status_code=403, content={"error": "license_required", "detail": res.get("error")})

    return await call_next(request)

# Register routers
app.include_router(ingest.router,    prefix="/api/ingest",    tags=["Ingest"])
app.include_router(cleanse.router,   prefix="/api/cleanse",   tags=["Cleanse"])
app.include_router(etl.router,       prefix="/api/etl",       tags=["ETL"])
app.include_router(eda.router,       prefix="/api/eda",       tags=["EDA"])
app.include_router(charts.router,    prefix="/api/charts",    tags=["Charts"])
app.include_router(narrative.router, prefix="/api/narrative", tags=["Narrative"])
app.include_router(license.router,   prefix="/api/license",   tags=["License"])
app.include_router(config.router,    prefix="/api/config",    tags=["Config"])


@app.get("/")
def root():
    return {"status": "ok", "app": "DataLytica", "version": "1.0.0"}


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "DataLytica", "version": "1.0.0"}