"""Database configuration and connection management."""
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Determine database path - support /app/data for production, local file otherwise
DB_PATH = os.getenv("DATABASE_PATH")
if not DB_PATH:
    # Try /app/data for Railway/Docker, fall back to local
    data_dir = Path("/app/data")
    if data_dir.exists():
        # Railway volume is mounted, use it
        DB_PATH = str(data_dir / "counts.db")
    elif os.getenv("RAILWAY_ENVIRONMENT"):
        # On Railway but volume not mounted yet - use local path as fallback
        print("WARNING: Railway detected but /app/data not found, using local path")
        DB_PATH = "counts.db"
    else:
        # Local development
        DB_PATH = "counts.db"

print(f"Using database path: {DB_PATH}")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    future=True,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Get database session for dependency injection."""
    async with async_session_maker() as session:
        yield session
