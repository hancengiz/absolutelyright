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
