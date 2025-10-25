# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A fun web application that tracks how many times Claude Code tells the user they are "absolutely right". It consists of:
- **Backend**: Python/FastAPI server with SQLite storage
- **Frontend**: Static HTML/JS/CSS served by the backend

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Or use a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run
```bash
# Run the server (serves on port 3003)
python src/main.py

# Or use uvicorn directly with auto-reload
uvicorn src.main:app --host 0.0.0.0 --port 3003 --reload
```

### Code Quality
```bash
# Format Python code
black src/

# Lint Python code
ruff check src/
# or
pylint src/
```

## Architecture

### Backend (`src/main.py`)
- **Framework**: FastAPI web framework with async/await
- **ORM**: SQLAlchemy with async SQLite support
- **Database**: SQLite database (`counts.db`) with aiosqlite for async operations
- **API Endpoints**:
  - `GET /api/today` - Returns today's count
  - `GET /api/history` - Returns all historical data
  - `POST /api/set` - Updates count for a specific day
- **Static Files**: Serves frontend from `frontend/` directory via FastAPI StaticFiles

### Frontend (`frontend/`)
- **index.html**: Main page displaying current count and chart
- **frontend.js**: Fetches data from API and renders historical chart using roughViz
- **style.css**: Styling for the application

### Python Modules (`src/`)
- **main.py**: FastAPI application with API endpoints and static file serving
- **models.py**: SQLAlchemy models (DayCount table)
- **database.py**: Database configuration and connection management

## Key Implementation Details

- The server binds to `0.0.0.0:3003` for network accessibility
- Uses Python `datetime` for date handling with `%Y-%m-%d` format
- Frontend auto-refreshes count every 5 seconds
- Chart visualization uses roughViz library for hand-drawn style charts
- Data persistence via SQLite database with automatic table creation on startup
- Database schema: `day_counts` table with:
  - `day` (TEXT PRIMARY KEY)
  - `patterns` (TEXT - JSON object with pattern counts)
  - `total_messages` (INTEGER)
- Supports dynamic pattern tracking (absolutely, right, perfect, excellent, etc.)

## Deployment

The application is deployed using Docker on Railway:
- **Dockerfile**: Multi-stage build with Python 3.11
- **Port**: 3003 (configurable via PORT environment variable)
- **Database**: SQLite file persisted in `/app/data` volume
- **Environment Variables**:
  - `PORT`: Server port (default: 3003)
  - `ABSOLUTELYRIGHT_SECRET`: Optional secret for API authentication
  - `DATABASE_PATH`: Custom database path (optional)

## Notes

- Frontend is served directly by the FastAPI server (no separate build process)
- No tests are currently implemented
- Database file `counts.db` is created automatically on first run
- Backend converted from Rust/Axum to Python/FastAPI while maintaining API compatibility
- Stop telling me I'm absolutely right.
