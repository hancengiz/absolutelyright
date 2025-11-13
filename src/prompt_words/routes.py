"""FastAPI routes for prompt words tracking."""
import os
import json
from datetime import datetime, timezone
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from src.database import get_session
from src.prompt_words.models import PromptWordCount


# Create router
router = APIRouter()


# Pydantic models for API
class SetPromptWordsRequest(BaseModel):
    day: str
    workstation_id: str
    total_user_messages: Optional[int] = None
    secret: Optional[str] = None

    class Config:
        extra = "allow"  # Allow additional fields for word counts


@router.get("/today")
async def get_today(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Get today's prompt word counts aggregated across all workstations."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Fetch ALL workstation records for today
    result = await session.execute(
        select(PromptWordCount).where(PromptWordCount.day == today)
    )
    word_counts = result.scalars().all()

    # Aggregate across workstations
    from collections import defaultdict
    aggregated_words: Dict[str, int] = defaultdict(int)
    aggregated_total = 0

    for record in word_counts:
        # Parse words JSON
        try:
            words = json.loads(record.words)
            for word, count in words.items():
                aggregated_words[word] += count
        except json.JSONDecodeError:
            pass
        aggregated_total += record.total_user_messages or 0

    # Build response (workstation_id hidden from API)
    response_data = dict(aggregated_words)
    response_data["total_user_messages"] = aggregated_total

    # Cache for 1 minute
    return JSONResponse(
        content=response_data,
        headers={"Cache-Control": "public, max-age=60"}
    )


@router.get("/history")
async def get_history(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Get historical prompt word counts aggregated across all workstations."""
    # Fetch all records ordered by day
    result = await session.execute(
        select(PromptWordCount).order_by(PromptWordCount.day)
    )
    all_records = result.scalars().all()

    # Group by day, aggregate across workstations
    from collections import defaultdict
    by_day: Dict[str, Dict] = defaultdict(lambda: {"words": defaultdict(int), "total": 0})

    for record in all_records:
        # Parse words JSON
        try:
            words = json.loads(record.words)
            for word, count in words.items():
                by_day[record.day]["words"][word] += count
        except json.JSONDecodeError:
            pass
        by_day[record.day]["total"] += record.total_user_messages or 0

    # Build response (workstation_id hidden from API)
    history = []
    for day in sorted(by_day.keys()):
        day_data = {"day": day}
        day_data.update(by_day[day]["words"])
        day_data["total_user_messages"] = by_day[day]["total"]
        history.append(day_data)

    # Cache for 5 minutes
    return JSONResponse(
        content=history,
        headers={"Cache-Control": "public, max-age=300"}
    )


@router.post("/set")
async def set_day(
    payload: SetPromptWordsRequest,
    session: AsyncSession = Depends(get_session)
) -> JSONResponse:
    """Set prompt word counts for a specific day."""
    # Check secret if ABSOLUTELYRIGHT_SECRET is set
    expected_secret = os.getenv("ABSOLUTELYRIGHT_SECRET")
    if expected_secret:
        if not payload.secret or payload.secret != expected_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid secret"
            )

    # Build words map - extract numeric values from additional fields
    words_map: Dict[str, int] = {}
    payload_dict = payload.model_dump()
    for key, value in payload_dict.items():
        # Skip known non-word fields
        if key in ["day", "total_user_messages", "secret", "workstation_id"]:
            continue
        # Include numeric values as word counts
        if isinstance(value, int):
            words_map[key] = value

    words_json = json.dumps(words_map)
    total_user_messages = payload.total_user_messages or 0

    # Check if record exists for this workstation
    result = await session.execute(
        select(PromptWordCount).where(
            PromptWordCount.day == payload.day,
            PromptWordCount.workstation_id == payload.workstation_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing record for this workstation
        existing.words = words_json
        existing.total_user_messages = total_user_messages
    else:
        # Create new record for this workstation
        new_record = PromptWordCount(
            day=payload.day,
            workstation_id=payload.workstation_id,
            words=words_json,
            total_user_messages=total_user_messages
        )
        session.add(new_record)

    await session.commit()

    return JSONResponse(content="ok")
