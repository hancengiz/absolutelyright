"""FastAPI backend for Absolutely Right tracking application."""
import os
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from src.database import init_db, get_session
from src.models import DayCount
from src.prompt_words.routes import router as prompt_words_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    await init_db()
    print(f"Database initialized")
    print(f"Server starting on port {os.getenv('PORT', 3003)}")
    yield
    # Shutdown (if needed)
    print("Server shutting down")


# Initialize FastAPI app with lifespan
app = FastAPI(title="Absolutely Right API", lifespan=lifespan)

# Include prompt words router
app.include_router(prompt_words_router, prefix="/api/things-i-tell-claude", tags=["things-i-tell-claude"])


# Pydantic models for API
class SetRequest(BaseModel):
    day: str
    workstation_id: str  # NEW: Required workstation identifier
    # Legacy fields for backward compatibility
    count: Optional[int] = None
    right_count: Optional[int] = None
    # New format - additional fields will be captured as patterns
    total_messages: Optional[int] = None
    secret: Optional[str] = None

    class Config:
        extra = "allow"  # Allow additional fields for patterns


@app.get("/api/today")
async def get_today(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Get today's counts aggregated across all workstations."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Fetch ALL workstation records for today
    result = await session.execute(
        select(DayCount).where(DayCount.day == today)
    )
    day_counts = result.scalars().all()

    # Aggregate across workstations
    from collections import defaultdict
    aggregated_patterns: Dict[str, int] = defaultdict(int)
    aggregated_total = 0

    for record in day_counts:
        # Parse patterns JSON
        try:
            patterns = json.loads(record.patterns)
            for pattern, count in patterns.items():
                aggregated_patterns[pattern] += count
        except json.JSONDecodeError:
            pass
        aggregated_total += record.total_messages or 0

    # Build response (workstation_id hidden from API)
    response_data = dict(aggregated_patterns)
    response_data["total_messages"] = aggregated_total

    # Cache for 1 minute
    return JSONResponse(
        content=response_data,
        headers={"Cache-Control": "public, max-age=60"}
    )


@app.get("/api/history")
async def get_history(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Get historical counts aggregated across all workstations."""
    # Fetch all records ordered by day
    result = await session.execute(
        select(DayCount).order_by(DayCount.day)
    )
    all_records = result.scalars().all()

    # Group by day, aggregate across workstations
    from collections import defaultdict
    by_day: Dict[str, Dict] = defaultdict(lambda: {"patterns": defaultdict(int), "total": 0})

    for record in all_records:
        # Parse patterns JSON
        try:
            patterns = json.loads(record.patterns)
            for pattern, count in patterns.items():
                by_day[record.day]["patterns"][pattern] += count
        except json.JSONDecodeError:
            pass
        by_day[record.day]["total"] += record.total_messages or 0

    # Build response (workstation_id hidden from API)
    history = []
    for day in sorted(by_day.keys()):
        day_data = {"day": day}
        day_data.update(by_day[day]["patterns"])
        day_data["total_messages"] = by_day[day]["total"]
        history.append(day_data)

    # Cache for 5 minutes
    return JSONResponse(
        content=history,
        headers={"Cache-Control": "public, max-age=300"}
    )


@app.get("/api/by-workstation")
async def get_by_workstation(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Get data grouped by workstation for debugging/inspection."""
    # Fetch all records ordered by day and workstation
    result = await session.execute(
        select(DayCount).order_by(DayCount.day, DayCount.workstation_id)
    )
    all_records = result.scalars().all()

    # Group by workstation, then by day
    from collections import defaultdict
    by_workstation: Dict[str, list] = defaultdict(list)

    for record in all_records:
        # Parse patterns JSON
        try:
            patterns = json.loads(record.patterns)
        except json.JSONDecodeError:
            patterns = {}

        day_data = {
            "day": record.day,
            "total_messages": record.total_messages or 0
        }
        day_data.update(patterns)
        by_workstation[record.workstation_id].append(day_data)

    # Build response with workstation_id exposed
    response = []
    for workstation_id in sorted(by_workstation.keys()):
        response.append({
            "workstation_id": workstation_id,
            "history": by_workstation[workstation_id]
        })

    # Cache for 1 minute
    return JSONResponse(
        content=response,
        headers={"Cache-Control": "public, max-age=60"}
    )


@app.get("/2")
async def workstations_view():
    """Serve the workstations view page."""
    from fastapi.responses import FileResponse
    return FileResponse("frontend/workstations.html")


@app.get("/things-i-tell-claude")
async def things_i_tell_claude_view():
    """Serve the things I tell Claude dashboard page."""
    from fastapi.responses import FileResponse
    return FileResponse("frontend/prompt_words/index.html")


@app.get("/prompt_words")
@app.get("/prompt-words")
async def redirect_prompt_words():
    """Redirect old prompt_words URLs to new things-i-tell-claude URL."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/things-i-tell-claude", status_code=301)


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
    payload_dict = payload.model_dump()
    for key, value in payload_dict.items():
        # Skip known non-pattern fields
        if key in ["day", "total_messages", "secret", "count", "right_count", "workstation_id"]:
            continue
        # Include numeric values as patterns
        if isinstance(value, int):
            patterns_map[key] = value

    patterns_json = json.dumps(patterns_map)
    total_messages = payload.total_messages or 0

    # Check if record exists for this workstation
    result = await session.execute(
        select(DayCount).where(
            DayCount.day == payload.day,
            DayCount.workstation_id == payload.workstation_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing record for this workstation
        existing.patterns = patterns_json
        existing.total_messages = total_messages
    else:
        # Create new record for this workstation
        new_record = DayCount(
            day=payload.day,
            workstation_id=payload.workstation_id,
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
