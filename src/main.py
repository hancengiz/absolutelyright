"""FastAPI backend for Absolutely Right tracking application."""
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from src.database import init_db, get_session
from src.models import DayCount


# Initialize FastAPI app
app = FastAPI(title="Absolutely Right API")


# Pydantic models for API
class SetRequest(BaseModel):
    day: str
    # Legacy fields for backward compatibility
    count: Optional[int] = None
    right_count: Optional[int] = None
    # New format - additional fields will be captured as patterns
    total_messages: Optional[int] = None
    secret: Optional[str] = None

    class Config:
        extra = "allow"  # Allow additional fields for patterns


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await init_db()
    print(f"Database initialized")
    print(f"Server starting on port {os.getenv('PORT', 3003)}")


@app.get("/api/today")
async def get_today(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Get today's counts for all patterns."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Fetch today's record
    result = await session.execute(
        select(DayCount).where(DayCount.day == today)
    )
    day_count = result.scalar_one_or_none()

    # Build response
    response_data: Dict[str, int] = {}

    if day_count:
        # Parse patterns JSON
        try:
            patterns = json.loads(day_count.patterns)
            response_data.update(patterns)
        except json.JSONDecodeError:
            pass
        response_data["total_messages"] = day_count.total_messages or 0
    else:
        # No data for today
        response_data["total_messages"] = 0

    # Cache for 1 minute
    return JSONResponse(
        content=response_data,
        headers={"Cache-Control": "public, max-age=60"}
    )


@app.get("/api/history")
async def get_history(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Get historical counts for all days."""
    # Fetch all records ordered by day
    result = await session.execute(
        select(DayCount).order_by(DayCount.day)
    )
    day_counts = result.scalars().all()

    # Build response
    history = []
    for day_count in day_counts:
        day_data = {"day": day_count.day}

        # Parse patterns JSON
        try:
            patterns = json.loads(day_count.patterns)
            day_data.update(patterns)
        except json.JSONDecodeError:
            pass

        day_data["total_messages"] = day_count.total_messages or 0
        history.append(day_data)

    # Cache for 5 minutes
    return JSONResponse(
        content=history,
        headers={"Cache-Control": "public, max-age=300"}
    )


@app.post("/api/set")
async def set_day(
    payload: SetRequest,
    session: AsyncSession = Depends(get_session)
) -> JSONResponse:
    """Set counts for a specific day."""
    # Check secret if ABSOLUTELYRIGHT_SECRET is set
    expected_secret = os.getenv("ABSOLUTELYRIGHT_SECRET")
    if expected_secret:
        if not payload.secret or payload.secret != expected_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid secret"
            )

    # Build patterns map - support both old and new formats
    patterns_map: Dict[str, int] = {}

    # Legacy support: if count or right_count are provided
    if payload.count is not None:
        patterns_map["absolutely"] = payload.count
    if payload.right_count is not None:
        patterns_map["right"] = payload.right_count

    # New format: extract numeric values from additional fields
    payload_dict = payload.dict()
    for key, value in payload_dict.items():
        # Skip known non-pattern fields
        if key in ["day", "total_messages", "secret", "count", "right_count"]:
            continue
        # Include numeric values as patterns
        if isinstance(value, int):
            patterns_map[key] = value

    patterns_json = json.dumps(patterns_map)
    total_messages = payload.total_messages or 0

    # Check if record exists
    result = await session.execute(
        select(DayCount).where(DayCount.day == payload.day)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing record
        existing.patterns = patterns_json
        existing.total_messages = total_messages
    else:
        # Create new record
        new_record = DayCount(
            day=payload.day,
            patterns=patterns_json,
            total_messages=total_messages
        )
        session.add(new_record)

    await session.commit()

    return JSONResponse(content="ok")


# Mount static files - serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 3003))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
