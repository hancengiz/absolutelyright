# absolutelyright

A scientifically rigorous tracking system for how often Claude Code validates my life choices.

This code powers the [https://cc.cengizhan.com/](https://cc.cengizhan.com/) website.

**Originally forked from** [yoavf/absolutelyright](https://github.com/yoavf/absolutelyright) which powers [absolutelyright.lol](https://absolutelyright.lol/)

---

![Claude Code Graph](frontend/assets/claude-code-graph.png)

## Project History

### Original Implementation (Forked)
- Rust/Axum backend with SQLite
- Simple frontend with roughViz charts
- Basic "absolutely right" and "right" pattern tracking

### Major Changes in This Fork

**Backend Migration (Rust → Python)**
- Converted from Rust/Axum to Python/FastAPI
- Switched to async SQLAlchemy with SQLite
- Maintained API compatibility for seamless migration
- Added support for dynamic pattern tracking

**Enhanced Pattern Tracking**
- Extended beyond "absolutely" and "right" to include:
  - "Perfect!" - Tracking perfect responses
  - "Excellent!" - Tracking excellent responses
- Configurable patterns via `scripts/patterns_config.json`
- Backend now accepts any pattern as a field in the API

**Infrastructure & Deployment**
- Added Docker support with multi-stage builds
- Railway deployment configuration
- Persistent volume setup for SQLite database
- Environment-based port configuration

**Automation & Monitoring**
- Real-time watcher script that monitors Claude Code conversations
- Backfill script to import historical data
- macOS LaunchAgent integration for automatic background monitoring
- Installation script for easy setup
- Upload logging to track sync operations

**Data Tracking Improvements**
- Total messages per day tracking
- Per-message pattern matching (not per-occurrence)
- Duplicate message ID detection
- Project-based breakdown of counts

---

## What This Repo Contains

- **Frontend** (`frontend/`) - Minimal HTML + JS, with charts drawn using [roughViz](https://www.jwilber.me/roughviz/)
- **Backend** (`src/`) - Python/FastAPI server with async SQLite storage
- **Scripts** (`scripts/`) - Python tools to collect and upload counts from Claude Code sessions
- **Docker** - Containerized deployment ready for Railway or any Docker host

**Currently Tracking:**
- Times Claude Code said you're "absolutely right"
- Times Claude Code said you're just "right"
- Times Claude Code said "Perfect!"
- Times Claude Code said "Excellent!"
- Total messages per day

---

## Getting Started (For Forks/Clones)

### Prerequisites

- Python 3.11+
- Claude Code installed locally
- (Optional) Railway account for deployment

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/hancengiz/absolutelyright-claude-code.git
cd absolutelyright-claude-code

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Patterns (Optional)

Edit `scripts/patterns_config.json` to customize what patterns to track:

```json
{
  "server_url": "http://localhost:3003",
  "patterns": {
    "absolutely": "You(?:'re| are) absolutely right",
    "right": "You(?:'re| are) right",
    "perfect": "Perfect!",
    "excellent": "Excellent!",
    "custom_pattern": "Your custom regex here"
  }
}
```

### Step 3: Run Locally

```bash
# Start the server
python src/main.py

# Or use uvicorn directly with auto-reload
uvicorn src.main:app --host 0.0.0.0 --port 3003 --reload

# Visit http://localhost:3003
```

The database (`counts.db`) will be created automatically on first run.

### Step 4: Backfill Historical Data

```bash
# This will scan your ~/.claude/projects directory
# and import all historical "absolutely right" counts

cd scripts
python3 backfill.py --upload http://localhost:3003
```

This script will:
1. Scan all your Claude Code project `.jsonl` files
2. Extract pattern matches from assistant messages
3. Prompt for confirmation before uploading
4. Upload daily aggregated counts to your local server

### Step 5: Setup Automatic Monitoring (macOS)

For continuous monitoring of new Claude Code conversations:

#### Option A: Manual Setup (Recommended)

1. **Generate a secret key:**
```bash
openssl rand -base64 32
# Save this secret for use in the next steps
```

2. **Create LaunchAgent plist file:**
```bash
# Create the LaunchAgents directory if it doesn't exist
mkdir -p ~/Library/LaunchAgents

# Create the plist file
cat > ~/Library/LaunchAgents/com.cengizhan.absolutelyright.watcher.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cengizhan.absolutelyright.watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/YOUR_USERNAME/code/absolutelyright-claude-code/scripts/watcher.py</string>
        <string>--secret</string>
        <string>YOUR_SECRET_HERE</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/code/absolutelyright-claude-code</string>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/code/absolutelyright-claude-code/logs/watcher.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/code/absolutelyright-claude-code/logs/watcher.error.log</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
EOF
```

3. **Edit the plist file to add your details:**
```bash
# Replace YOUR_USERNAME with your actual username
sed -i '' "s/YOUR_USERNAME/$(whoami)/g" ~/Library/LaunchAgents/com.cengizhan.absolutelyright.watcher.plist

# Replace YOUR_SECRET_HERE with your generated secret (manually edit the file)
nano ~/Library/LaunchAgents/com.cengizhan.absolutelyright.watcher.plist
```

4. **Load and start the LaunchAgent:**
```bash
launchctl load ~/Library/LaunchAgents/com.cengizhan.absolutelyright.watcher.plist
```

#### Option B: Quick Start (One-Time Run)

For testing or one-time use:
```bash
# Run in background with nohup
nohup python3 scripts/watcher.py --secret "YOUR_SECRET" >> logs/watcher.log 2>&1 &
```

**Note:** This will not survive reboots. Use the LaunchAgent method for persistent monitoring.

#### Verify It's Running

```bash
# Check if LaunchAgent is loaded
launchctl list | grep absolutelyright

# Check if process is running
ps aux | grep watcher.py | grep -v grep

# View logs (logs rotate daily, keeping 7 days)
tail -f logs/watcher.log
tail -f logs/watcher.error.log

# View upload history
tail -f logs/uploads.log
```

#### Managing the Service

```bash
# Stop the watcher
launchctl unload ~/Library/LaunchAgents/com.cengizhan.absolutelyright.watcher.plist

# Start the watcher
launchctl load ~/Library/LaunchAgents/com.cengizhan.absolutelyright.watcher.plist

# Restart the watcher
launchctl unload ~/Library/LaunchAgents/com.cengizhan.absolutelyright.watcher.plist && \
launchctl load ~/Library/LaunchAgents/com.cengizhan.absolutelyright.watcher.plist
```

**What the watcher does:**
- Monitors Claude Code conversations every 2 seconds
- Detects pattern matches in real-time
- Uploads counts to your server with the secret key
- Runs automatically on system startup
- Restarts automatically if it crashes
- Logs rotate daily at midnight (keeps 7 days)

### Step 6: Deploy to Railway (Optional)

1. **Create a Railway project**
   - Connect your GitHub repository
   - Railway will auto-detect the Dockerfile

2. **Configure environment variables:**
   ```
   PORT=3003  # Railway will override this with its own PORT
   ABSOLUTELYRIGHT_SECRET=YOUR_GENERATED_SECRET
   DATABASE_PATH=/app/data/counts.db  # Optional, defaults to counts.db
   ```

3. **Add a volume:**
   - Mount point: `/app/data`
   - This ensures your SQLite database persists across deployments

4. **Deploy:**
   - Railway will automatically build and deploy
   - Health check endpoint: `/api/today`

5. **Update your local config:**
   Edit `scripts/patterns_config.json`:
   ```json
   {
     "server_url": "https://your-app.railway.app",
     ...
   }
   ```

6. **Reinstall watcher with new URL:**
   ```bash
   ./scripts/install-watcher.sh "YOUR_SECRET"
   ```

---

## Project Structure

```
absolutelyright/
├── frontend/              # Static web frontend
│   ├── index.html        # Main page
│   ├── frontend.js       # Data fetching and chart rendering
│   └── style.css         # Styling
├── src/                  # Python backend
│   ├── main.py          # FastAPI application and routes
│   ├── models.py        # SQLAlchemy models
│   └── database.py      # Database configuration
├── scripts/             # Data collection tools
│   ├── backfill.py      # Import historical data
│   ├── watcher.py       # Real-time monitoring
│   ├── claude_counter.py # Core counting logic
│   ├── patterns_config.json # Pattern definitions
│   └── install-watcher.sh   # macOS service installer
├── Dockerfile           # Container configuration
├── railway.json         # Railway deployment config
├── requirements.txt     # Python dependencies
└── counts.db           # SQLite database (auto-created)
```

---

## API Reference

### `GET /api/today`
Returns today's pattern counts (aggregated across all workstations).

**Response:**
```json
{
  "absolutely": 3,
  "right": 2,
  "perfect": 15,
  "excellent": 8,
  "total_messages": 450
}
```

**Cache:** 1 minute

### `GET /api/history`
Returns all historical data, ordered by date (aggregated across all workstations).

**Response:**
```json
[
  {
    "day": "2025-10-22",
    "absolutely": 4,
    "right": 4,
    "perfect": 47,
    "excellent": 12,
    "total_messages": 1057
  },
  ...
]
```

**Cache:** 5 minutes

### `GET /api/by-workstation`
Returns data grouped by workstation for debugging and inspection.

**Response:**
```json
[
  {
    "workstation_id": "cengizs-MacBook-Pro",
    "history": [
      {
        "day": "2025-10-22",
        "absolutely": 4,
        "right": 4,
        "perfect": 47,
        "excellent": 12,
        "total_messages": 1057
      },
      ...
    ]
  },
  ...
]
```

**Cache:** 1 minute

**Use cases:**
- Debug which workstation contributed data
- Verify all machines are uploading correctly
- Inspect data distribution across workstations

### `POST /api/set`
Upload counts for a specific day and workstation.

**Request:**
```json
{
  "day": "2025-10-25",
  "workstation_id": "cengizs-MacBook-Pro",
  "absolutely": 3,
  "right": 2,
  "perfect": 75,
  "excellent": 20,
  "total_messages": 2024,
  "secret": "YOUR_SECRET"
}
```

**Response:**
```json
"ok"
```

**Notes:**
- Requires `ABSOLUTELYRIGHT_SECRET` environment variable to be set
- Requires `workstation_id` field (automatically added by scripts)
- Supports dynamic pattern fields (any numeric field becomes a pattern)
- Each workstation's data is stored separately and aggregated on read
- Legacy fields `count` and `right_count` are supported for backward compatibility

---

## Development

### Code Quality

```bash
# Format Python code
black src/

# Lint Python code
ruff check src/
# or
pylint src/
```

### Database Schema

```sql
CREATE TABLE day_counts (
    day VARCHAR NOT NULL,           -- Date in YYYY-MM-DD format
    workstation_id VARCHAR NOT NULL, -- Machine identifier (e.g., "cengizs-MacBook-Pro")
    patterns TEXT NOT NULL,          -- JSON object with pattern counts
    total_messages INTEGER,          -- Total assistant messages that day
    PRIMARY KEY (day, workstation_id) -- Composite key for multi-workstation support
);
```

**Example `patterns` JSON:**
```json
{
  "absolutely": 4,
  "right": 4,
  "perfect": 47,
  "excellent": 12
}
```

**Multi-Workstation Support:**
- Each workstation's data is stored separately
- API endpoints (`/api/today`, `/api/history`) automatically aggregate across all workstations
- Workstation ID is automatically detected (macOS LocalHostName or hostname)
- No data conflicts when running from multiple machines

### Environment Variables

- `PORT` - Server port (default: 3003)
- `ABSOLUTELYRIGHT_SECRET` - API secret for uploads (optional, but recommended)
- `DATABASE_PATH` - Custom database file path (default: `counts.db`)
- `CLAUDE_PROJECTS` - Claude projects directory (default: `~/.claude/projects`)

---

## Troubleshooting

### Database not found
The database is created automatically. If you see errors:
```bash
# Check database file exists
ls -la counts.db

# Check permissions
chmod 644 counts.db
```

### Watcher not uploading
```bash
# Check if service is running
launchctl list | grep absolutelyright

# Check logs for errors
tail -f ~/Library/Logs/absolutelyright-watcher.error.log

# Restart service
launchctl unload ~/Library/LaunchAgents/com.absolutelyright.watcher.plist
launchctl load ~/Library/LaunchAgents/com.absolutelyright.watcher.plist
```

### Railway deployment fails
- Ensure `ABSOLUTELYRIGHT_SECRET` environment variable is set
- Check that volume is mounted at `/app/data`
- Verify health check endpoint `/api/today` is accessible
- Check deployment logs in Railway dashboard

### No historical data
- Verify Claude Code projects exist at `~/.claude/projects`
- Check that `.jsonl` files contain data
- Run backfill manually to see what's found:
  ```bash
  python3 scripts/backfill.py  # Don't use --upload to just see counts
  ```

---

## Contributing

This is a personal fork, but feel free to:
1. Fork this repo for your own tracking
2. Submit issues for bugs
3. Create PRs for improvements

---

## License

MIT License - see the original [yoavf/absolutelyright](https://github.com/yoavf/absolutelyright) repository.

---

## Acknowledgments

- Original concept and implementation by [yoavf](https://github.com/yoavf)
- Charts powered by [roughViz](https://www.jwilber.me/roughviz/)
- Inspired by Claude Code's encouraging (if sometimes excessive) validation
