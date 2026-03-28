from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.config import settings
from app.routers import auth, companies, uploads, reports, audit, exports, audit_checks
import app.models  # ensure all models are registered

# Create tables (new installs)
Base.metadata.create_all(bind=engine)


def _run_migrations():
    """Safely add new columns to existing DBs without breaking old installs.
    Works for both SQLite (PRAGMA) and PostgreSQL (IF NOT EXISTS)."""
    from sqlalchemy import text
    dialect = engine.dialect.name
    with engine.connect() as conn:
        if dialect == "sqlite":
            existing = {row[1] for row in conn.execute(text("PRAGMA table_info(data_dumps)")).fetchall()}
            if "progress_pct" not in existing:
                conn.execute(text("ALTER TABLE data_dumps ADD COLUMN progress_pct INTEGER DEFAULT 0"))
            if "progress_stage" not in existing:
                conn.execute(text("ALTER TABLE data_dumps ADD COLUMN progress_stage TEXT"))
        else:
            # PostgreSQL supports IF NOT EXISTS — safe even if columns already exist
            conn.execute(text("ALTER TABLE IF EXISTS data_dumps ADD COLUMN IF NOT EXISTS progress_pct INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE IF EXISTS data_dumps ADD COLUMN IF NOT EXISTS progress_stage TEXT"))
        conn.commit()


_run_migrations()

app = FastAPI(
    title="TallyToInsights API",
    description="Comprehensive Tally data analysis, audit intelligence, and financial reporting platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(uploads.router)
app.include_router(reports.router)
app.include_router(audit.router)
app.include_router(exports.router)
app.include_router(audit_checks.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TallyToInsights"}


@app.get("/")
def root():
    return {"message": "TallyToInsights API", "docs": "/api/docs"}
