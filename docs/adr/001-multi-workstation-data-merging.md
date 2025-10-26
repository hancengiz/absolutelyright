# ADR 001: Multi-Workstation Data Merging

**Status:** Proposed
**Date:** 2025-10-26
**Deciders:** Han Cengiz

## Context

The AbsolutelyRight tracker currently uses a **SET** (replace) operation when uploading pattern counts via the `/api/set` endpoint. This creates a data integrity problem when running the backfill script from multiple workstations:

### Current Behavior
```python
# src/main.py:150-153
if existing:
    existing.patterns = patterns_json      # REPLACES entire data
    existing.total_messages = total_messages
```

### The Problem

Each workstation has its own `~/.claude/projects` directory containing different conversation histories:

1. **Workstation A** scans local conversations → finds 5 "absolutely" on 2025-10-26
2. **Workstation B** scans local conversations → finds 3 "absolutely" on 2025-10-26
3. Both upload to API
4. **Last upload wins** - data is replaced, not merged

**Result:** Lost data. Only the last workstation's counts are preserved, missing conversations unique to other machines.

### Current Workarounds Considered

1. ❌ **Single source** - Only run from one machine (loses data from other workstations)
2. ❌ **Manual merge** - Export JSON and manually combine (error-prone, tedious)
3. ✅ **API merge logic** - Server-side intelligent merging (proposed solution)

## Decision

We will implement **per-workstation data storage** with **API-level aggregation**. Each workstation stores its own counts, and the API merges them when serving data.

### Simple Grouping Approach

This is an intentional **breaking change** to fix data integrity. We will:
- Modify database schema to add `workstation_id` column
- Each machine UPSERTs only its own data (no conflicts!)
- GET endpoints aggregate across all workstations
- Machine names never exposed to UI (internal only)
- Accept database reset for clean migration

#### Database Schema Changes

Modify existing `day_counts` table to add workstation tracking:

```sql
-- New schema
CREATE TABLE day_counts (
    day TEXT NOT NULL,
    workstation_id TEXT NOT NULL,
    patterns TEXT NOT NULL DEFAULT '{}',
    total_messages INTEGER DEFAULT 0,
    PRIMARY KEY (day, workstation_id)  -- Composite key!
);

CREATE INDEX idx_day ON day_counts(day);
```

**Key change:** Composite primary key `(day, workstation_id)` means each workstation has its own record per day.

#### API Changes

**POST `/api/set`** (modified):
- Now requires `workstation_id` parameter
- UPSERTs data for that specific workstation only
- No conflicts - each machine owns its own records

**GET `/api/today`** and **GET `/api/history`** (modified):
- Query all workstations for the requested day(s)
- **SUM** counts across all workstations
- Return aggregated data (machines invisible to client)

#### Request Format (POST /api/set)

```json
{
  "day": "2025-10-26",
  "workstation_id": "macbook-pro-home",
  "absolutely": 5,
  "right": 3,
  "perfect": 10,
  "excellent": 2,
  "total_messages": 150,
  "secret": "..."
}
```

Simple! Just add `workstation_id` to existing format.

#### API Logic

**POST /api/set** (simplified):

```python
@app.post("/api/set")
async def set_day(payload: SetRequest, session: AsyncSession):
    # Authentication check (unchanged)
    ...

    # Build patterns map (unchanged)
    patterns_map = {...}
    patterns_json = json.dumps(patterns_map)
    total_messages = payload.total_messages or 0

    # UPSERT for this workstation only
    result = await session.execute(
        select(DayCount).where(
            DayCount.day == payload.day,
            DayCount.workstation_id == payload.workstation_id  # NEW
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update THIS workstation's data
        existing.patterns = patterns_json
        existing.total_messages = total_messages
    else:
        # Create new record for THIS workstation
        new_record = DayCount(
            day=payload.day,
            workstation_id=payload.workstation_id,  # NEW
            patterns=patterns_json,
            total_messages=total_messages
        )
        session.add(new_record)

    await session.commit()
    return JSONResponse(content="ok")
```

**GET /api/today** (aggregation):

```python
@app.get("/api/today")
async def get_today(session: AsyncSession):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Fetch ALL workstation records for today
    result = await session.execute(
        select(DayCount).where(DayCount.day == today)
    )
    day_counts = result.scalars().all()

    # Aggregate across workstations
    aggregated_patterns = defaultdict(int)
    aggregated_total = 0

    for record in day_counts:
        patterns = json.loads(record.patterns)
        for pattern, count in patterns.items():
            aggregated_patterns[pattern] += count
        aggregated_total += record.total_messages or 0

    # Return merged data (workstation_id hidden)
    response_data = dict(aggregated_patterns)
    response_data["total_messages"] = aggregated_total

    return JSONResponse(content=response_data, headers={"Cache-Control": "public, max-age=60"})
```

**GET /api/history** (similar aggregation):

```python
@app.get("/api/history")
async def get_history(session: AsyncSession):
    result = await session.execute(select(DayCount).order_by(DayCount.day))
    all_records = result.scalars().all()

    # Group by day, aggregate across workstations
    by_day = defaultdict(lambda: {"patterns": defaultdict(int), "total": 0})

    for record in all_records:
        patterns = json.loads(record.patterns)
        for pattern, count in patterns.items():
            by_day[record.day]["patterns"][pattern] += count
        by_day[record.day]["total"] += record.total_messages or 0

    # Build response
    history = []
    for day in sorted(by_day.keys()):
        day_data = {"day": day}
        day_data.update(by_day[day]["patterns"])
        day_data["total_messages"] = by_day[day]["total"]
        history.append(day_data)

    return JSONResponse(content=history, headers={"Cache-Control": "public, max-age=300"})
```

**GET /api/by-workstation** (new - per-workstation view):

```python
@app.get("/api/by-workstation")
async def get_by_workstation(session: AsyncSession):
    """Get data grouped by workstation for debugging/inspection."""
    result = await session.execute(select(DayCount).order_by(DayCount.day, DayCount.workstation_id))
    all_records = result.scalars().all()

    # Group by workstation, then by day
    by_workstation = defaultdict(lambda: [])

    for record in all_records:
        patterns = json.loads(record.patterns)
        day_data = {
            "day": record.day,
            "total_messages": record.total_messages
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

    return JSONResponse(content=response, headers={"Cache-Control": "public, max-age=60"})
```

This endpoint is useful for:
- **Debugging**: See which workstation contributed which data
- **Verification**: Ensure all machines are uploading correctly
- **Inspection**: Understand data distribution across workstations

#### Client Script Changes

Update `scripts/claude_counter.py`:

```python
# Add workstation identification
import os
import socket
import subprocess
import platform

def get_workstation_id():
    """Get a stable, friendly workstation identifier"""
    # Check for environment variable first (allows manual override)
    if os.environ.get("WORKSTATION_ID"):
        return os.environ.get("WORKSTATION_ID")

    # On macOS, use LocalHostName (clean, stable, user-friendly)
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["scutil", "--get", "LocalHostName"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

    # Fallback to socket.gethostname() for other platforms
    return socket.gethostname()

WORKSTATION_ID = get_workstation_id()
# Example: "cengizs-MacBook-Pro" on macOS

def upload_to_api(api_url, secret, date_str, patterns_dict=None, total_messages=None):
    """Upload with workstation ID"""
    data = {
        "day": date_str,
        "workstation_id": WORKSTATION_ID,  # NEW - just add this!
        "total_messages": total_messages,
        "secret": secret
    }

    # Add pattern counts
    if patterns_dict:
        data.update(patterns_dict)

    # POST to /api/set (same endpoint!)
    ...
```

That's it! Just add `workstation_id` to the existing payload. The ID will be stable and user-friendly (e.g., `cengizs-MacBook-Pro`).

## Consequences

### Positive

✅ **Accurate counts** - No data loss from multiple workstations
✅ **Idempotent** - Re-running backfill from same machine is safe (UPSERT)
✅ **Simple** - Just add `workstation_id` to schema and requests
✅ **Clean** - Each machine owns its own data, no conflicts
✅ **Transparent** - API hides machine details from UI
✅ **Auditable** - Can query per-workstation data if needed (debugging)

### Negative

⚠️ **Breaking change** - Database schema changes, scripts must be updated
⚠️ **Database reset** - Historical data will be wiped (acceptable for clean start)
⚠️ **Slightly more storage** - Multiple records per day (one per workstation)

### Neutral

🔄 **Workstation ID management** - Users need to set `WORKSTATION_ID` env var (defaults to hostname)
🔄 **One-time migration** - All clients update at once, no compatibility layer needed
🔄 **Minimal code changes** - Just add one field to schema and aggregate on read

## Implementation Plan

### Phase 1: Database Schema Update
1. **Backup existing database from Railway**:
   ```bash
   # Install Railway CLI if needed
   npm install -g @railway/cli

   # Login to Railway
   railway login

   # Link to project
   railway link

   # Download database file
   railway run --service=<service-name> cat /app/data/counts.db > counts_backup_$(date +%Y%m%d).db
   # Or if database is in root: railway run cat counts.db > counts_backup_$(date +%Y%m%d).db
   ```
2. **Modify `src/models.py`**: Add `workstation_id` column, change primary key to `(day, workstation_id)`
3. **Update `src/database.py`**: Ensure clean table creation
4. **Delete existing database** (Railway: delete volume or reset counts.db)
5. Test schema locally

### Phase 2: API Modification
1. **Update Pydantic models** (`src/main.py`): Add `workstation_id` field to `SetRequest`
2. **Modify POST `/api/set`**: Update WHERE clause to use composite key
3. **Modify GET `/api/today`**: Add aggregation logic across workstations
4. **Modify GET `/api/history`**: Add aggregation logic across workstations
5. Test API locally

### Phase 3: Client Updates
1. **Update `scripts/claude_counter.py`**:
   - Add `get_workstation_id()` function (uses macOS LocalHostName or socket.gethostname())
   - Include in upload payload
2. **Update `scripts/backfill.py`**: Same changes
3. **Update `scripts/watcher.py`**: Same changes
4. Test locally with workstation ID detection

### Phase 4: Coordinated Deployment
1. Deploy new API to Railway
2. Delete/reset database on Railway
3. Update client scripts on all workstations
4. Run fresh backfill from each workstation
5. Verify data is merged correctly on frontend

### Phase 5: Documentation
1. Update README with breaking change notice
2. Document `WORKSTATION_ID` environment variable
3. Add multi-workstation setup guide

## Alternatives Considered

### Alternative 1: New API Endpoint (Backward Compatible)
**Approach:** Add `/api/set-incremental` alongside existing `/api/set`.

**Rejected because:**
- Unnecessary complexity (maintaining two endpoints)
- No existing users to maintain compatibility for
- Confusion about which endpoint to use
- Breaking change is acceptable for this project

### Alternative 2: Client-Side Merge
**Approach:** Clients fetch existing counts, merge locally, then upload total.

**Rejected because:**
- Race conditions between fetch and upload
- More network round-trips
- Complexity pushed to client
- No audit trail

### Alternative 3: Last-Write-Wins with Timestamps
**Approach:** Keep current behavior but add timestamps, warn users.

**Rejected because:**
- Doesn't solve the fundamental problem
- Data still lost
- Confusing user experience

### Alternative 4: Separate Databases per Workstation
**Approach:** Each workstation uploads to its own database/namespace.

**Rejected because:**
- Complex aggregation queries
- No single source of truth
- UI needs to query multiple sources
- Operational overhead

## References

- Current API implementation: `src/main.py:107-165`
- Backfill script: `scripts/backfill.py`
- Database schema: `src/models.py`
- Related issue: Multi-workstation data integrity

## Notes

- Consider adding a `/api/stats` endpoint showing per-workstation contributions
- Future: Could add UI to show which workstation contributed which data
- Future: Add cleanup job to archive old `processed_messages` (>90 days)
