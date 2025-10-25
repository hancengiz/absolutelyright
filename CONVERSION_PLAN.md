# Rust to Python Conversion Plan

## Overview
Converting the "Absolutely Right" backend from Rust/Axum to Python/FastAPI while maintaining all functionality and keeping the frontend unchanged.

## Current Architecture

### Backend (Rust)
- **Framework**: Axum 0.7 with Tokio async runtime
- **Database**: SQLite via tokio-rusqlite
- **Port**: 3003 (binds to 0.0.0.0)
- **Static Files**: Tower-HTTP ServeDir
- **Key Features**:
  - 3 API endpoints (today, history, set)
  - Pattern-based counting system
  - SQLite data persistence
  - Cache control headers
  - Secret-based authentication

### Frontend (Vanilla JS)
- Static HTML/CSS/JavaScript
- roughViz library for hand-drawn charts
- Dynamic pattern visualization
- No build process required

### Python Scripts (Already Python)
- `claude_counter.py` - Pattern matching utilities
- `watcher.py` - File watcher for Claude projects
- `backfill.py` - Historical data processing

## Target Architecture

### New Backend (Python)
- **Framework**: FastAPI (async, modern, type-safe)
- **Database**: SQLAlchemy ORM with SQLite
- **Port**: 3003 (maintain compatibility)
- **Static Files**: FastAPI StaticFiles
- **Key Features**: All current features maintained

### Frontend (No Changes)
- Keep all existing HTML/CSS/JavaScript
- Continue using roughViz for charts
- No modifications needed

### Scripts (No Changes)
- All Python scripts remain unchanged
- Will work seamlessly with new backend

## Conversion Tasks

### 1. Project Setup
- [ ] Create new Python project structure
- [ ] Create `requirements.txt` with dependencies
- [ ] Set up virtual environment
- [ ] Create `src/` directory for Python backend
- [ ] Create new `Dockerfile` for Python/FastAPI

### 2. Database Layer
- [ ] Create `src/database.py` for database connection
- [ ] Create `src/models.py` with SQLAlchemy models
- [ ] Define `DayCount` model matching current schema:
  - `day` (TEXT PRIMARY KEY)
  - `patterns` (TEXT - JSON)
  - `total_messages` (INTEGER)
- [ ] Add database initialization (create tables if not exist)
- [ ] Support configurable database path via environment variable

### 3. API Endpoints

#### GET /api/today
- [ ] Fetch today's count from database
- [ ] Parse patterns JSON
- [ ] Return combined dictionary with patterns + total_messages
- [ ] Add cache headers (public, max-age=60)

#### GET /api/history
- [ ] Fetch all historical records
- [ ] Parse patterns JSON for each day
- [ ] Return array of DayCount objects
- [ ] Add cache headers (public, max-age=300)

#### POST /api/set
- [ ] Accept JSON payload with day, patterns, total_messages
- [ ] Support legacy format (count, right_count)
- [ ] Check ABSOLUTELYRIGHT_SECRET environment variable
- [ ] Return 401 if secret mismatch
- [ ] Upsert to database (INSERT ... ON CONFLICT UPDATE)

### 4. Static File Serving
- [ ] Mount `/frontend` directory as static files
- [ ] Serve index.html as default for `/`
- [ ] Add cache control headers (no-cache for development)

### 5. Configuration
- [ ] Read `ABSOLUTELYRIGHT_SECRET` from environment
- [ ] Bind to 0.0.0.0:3003 (or PORT env variable for Railway)
- [ ] Add proper CORS headers if needed

### 6. Testing
- [ ] Test all API endpoints manually
- [ ] Verify database reads/writes
- [ ] Test secret authentication
- [ ] Verify frontend loads correctly
- [ ] Test chart rendering with real data

### 7. Documentation
- [ ] Update `CLAUDE.md` with Python instructions
- [ ] Add Python build/run commands
- [ ] Document dependencies
- [ ] Add migration notes for existing deployments

## File Structure

### New Files
```
/src/
  main.py              # FastAPI application entry point
  models.py            # SQLAlchemy models
  database.py          # Database configuration and connection

/requirements.txt      # Python dependencies
/Dockerfile            # Updated for Python (replaces Rust version)

/counts.db            # SQLite database (existing, no changes)
```

### Unchanged Files
```
/frontend/            # Static files (HTML, CSS, JS)
  index.html
  frontend.js
  style.css
  display_config.json

/scripts/             # Python helper scripts
  claude_counter.py
  watcher.py
  backfill.py
  patterns_config.json
```

### Files to Remove/Archive
```
/src/main.rs          # Old Rust backend
/Cargo.toml           # Rust dependencies
/Cargo.lock
/target/              # Rust build artifacts
```

## Dependencies (requirements.txt)

```
fastapi==0.109.0      # Web framework
uvicorn[standard]==0.27.0  # ASGI server
sqlalchemy==2.0.25    # ORM
aiosqlite==0.19.0     # Async SQLite driver
python-dotenv==1.0.0  # Environment variables
```

## Development Commands

### Current (Rust)
```bash
cargo build
cargo run
cargo fmt
cargo clippy
```

### New (Python)
```bash
# Setup
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run
python src/main.py
# or
uvicorn src.main:app --host 0.0.0.0 --port 3003 --reload

# Format
black src/
# or
ruff format src/

# Lint
ruff check src/
# or
pylint src/
```

## API Compatibility

All APIs remain 100% compatible:

### GET /api/today
**Response**:
```json
{
  "absolutely": 5,
  "right": 3,
  "perfect": 0,
  "excellent": 1,
  "total_messages": 42
}
```

### GET /api/history
**Response**:
```json
[
  {
    "day": "2025-10-24",
    "absolutely": 5,
    "right": 3,
    "perfect": 0,
    "excellent": 1,
    "total_messages": 42
  },
  ...
]
```

### POST /api/set
**Request**:
```json
{
  "day": "2025-10-24",
  "absolutely": 5,
  "right": 3,
  "perfect": 0,
  "excellent": 1,
  "total_messages": 42,
  "secret": "optional-secret-key"
}
```

**Response**: `"ok"`

## Migration Steps

### For Local Development
1. Keep existing `counts.db` database
2. Install Python dependencies
3. Run new Python backend
4. Test all endpoints
5. Archive old Rust code

### For Production (Railway with Docker)
1. Replace Dockerfile with Python version
2. Ensure environment variables are set (PORT, ABSOLUTELYRIGHT_SECRET)
3. Deploy new version (Railway will detect Dockerfile automatically)
4. Verify database persists correctly in `/app/data` volume

## Risk Assessment

### Low Risk ✅
- Frontend requires no changes
- Database schema stays the same
- API contracts remain identical
- Python scripts already exist and work

### Medium Risk ⚠️
- Switching from Rust to Python in Docker container
- Need to ensure async database operations work correctly
- Must verify database persistence in Docker volume
- Cache headers must match exactly for performance

### Mitigation
- Test thoroughly in local environment first
- Keep Rust version as fallback during transition
- Monitor logs during initial deployment
- Test with real watcher.py to ensure integration works

## Success Criteria

- ✅ All 3 API endpoints work identically
- ✅ Frontend loads and displays data correctly
- ✅ Charts render with roughViz
- ✅ Database reads/writes work
- ✅ Secret authentication functions
- ✅ Python scripts (watcher.py) can upload data
- ✅ No performance degradation
- ✅ Deployment to Railway succeeds

## Timeline Estimate

- **Setup & Models**: 30 minutes
- **API Endpoints**: 1 hour
- **Static Files**: 20 minutes
- **Testing**: 1 hour
- **Documentation**: 30 minutes
- **Total**: ~3 hours

## Questions to Resolve

1. ✅ Web framework choice: FastAPI selected
2. ✅ Database approach: SQLAlchemy ORM
3. ✅ Frontend handling: Keep vanilla JS
4. ✅ Hosting: Railway (already using)
5. ⏳ Code formatting: Use Black/Ruff?
6. ⏳ Type hints: Use mypy for type checking?

## Notes

- The conversion maintains 100% API compatibility
- No frontend changes ensure zero user impact
- Existing data in `counts.db` will work without migration
- Python scripts already integrated, no changes needed
- FastAPI provides automatic API documentation at `/docs`
