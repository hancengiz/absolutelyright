# Claude "Absolutely Right" Counter Script

Track patterns like "You're absolutely right!" in Claude Code conversations. 

## Usage

```bash
# Backfill historical data
python3 backfill.py --upload http://localhost:3003 [SECRET]

# Real-time monitoring (will backfill all of today's data)
python3 watcher.py --upload http://localhost:3003 [SECRET]
```

Backfill asks for confirmation before bulk uploads.

## Scheduling on macOS

Keep the watcher running automatically using launchd.

### 1. Generate a Secret

```bash
openssl rand -base64 32
```

Save this secret - you'll need it for both the server and the launch agent.

Set the secret on your server:
```bash
export ABSOLUTELYRIGHT_SECRET="[YOUR_SECRET]"
```

### 2. Create Launch Agent

Create `~/Library/LaunchAgents/com.absolutelyright.watcher.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.absolutelyright.watcher</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/FULL/PATH/TO/scripts/watcher.py</string>
        <string>--upload</string>
        <string>http://your-server.com</string>
        <string>[YOUR_SECRET]</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/Library/Logs/absolutelyright-watcher.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/Library/Logs/absolutelyright-watcher.error.log</string>
</dict>
</plist>
```

### 3. Load and Start

```bash
# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.absolutelyright.watcher.plist

# Check if running
launchctl list | grep absolutelyright

# View logs
tail -f ~/Library/Logs/absolutelyright-watcher.log
```

### Management Commands

```bash
# Stop
launchctl stop com.absolutelyright.watcher

# Start
launchctl start com.absolutelyright.watcher

# Unload (disable)
launchctl unload ~/Library/LaunchAgents/com.absolutelyright.watcher.plist

# Reload after editing plist
launchctl unload ~/Library/LaunchAgents/com.absolutelyright.watcher.plist
launchctl load ~/Library/LaunchAgents/com.absolutelyright.watcher.plist
```

## Patterns

Defined in `claude_counter.py`:
- **absolutely**: `You(?:'re| are) absolutely right`
- **right**: `You(?:'re| are) right`

Add patterns by editing the `PATTERNS` dict:
```python
PATTERNS = {
    "absolutely": r"You(?:'re| are) absolutely right",
    "right": r"You(?:'re| are) right",
    "perfect": r"Perfect!"  # New pattern
}
```

## Environment

```bash
export CLAUDE_PROJECTS=/path/to/projects  # Default: ~/.claude/projects
```

## Data Files

Stored in `~/.absolutelyright/`:
- `daily_{pattern}_counts.json` - Per-pattern daily counts
- `project_counts.json` - Project breakdown
- `processed_ids.json` - Processed message IDs

## API

Uploads to `/api/set`:
```json
{
  "day": "2024-01-15",
  "count": 5,
  "right_count": 12,
  "secret": "optional_secret"
}
```
