#!/usr/bin/env python3
import os
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

CLAUDE_PROJECTS_BASE = os.environ.get(
    "CLAUDE_PROJECTS", os.path.expanduser("~/.claude/projects")
)
DATA_DIR = os.path.expanduser("~/.absolutelyright")

# Get script directory for logging
SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
UPLOAD_LOG_FILE = LOG_DIR / "uploads.log"

PATTERNS = {
    "absolutely": r"You(?:'re| are) absolutely right",
    "right": r"You(?:'re| are) right",
    "perfect": r"Perfect!",
    "excellent": r"Excellent!",
}

# Additional pattern ideas (add to PATTERNS dict to track):
# "issue": r"I see the issue",
# "great": r"(?:That's |)great!",
# "exactly": r"(?:That's |)exactly right"


def log_upload(api_url, data, status, response_text=None, error=None):
    """Log upload attempts to file"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "url": api_url,
            "data": {k: v for k, v in data.items() if k != "secret"},  # Don't log secret
            "status": status,
        }
        if response_text:
            log_entry["response"] = response_text
        if error:
            log_entry["error"] = str(error)

        with open(UPLOAD_LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        # Don't fail if logging fails
        print(f"  Warning: Could not write to log: {e}")


def upload_to_api(api_url, secret, date_str, patterns_dict=None, total_messages=None, **legacy_kwargs):
    """
    Upload counts to API. Returns True/False/'STOP'

    Args:
        api_url: API endpoint URL
        secret: Optional API secret
        date_str: Date in YYYY-MM-DD format
        patterns_dict: Dictionary of pattern_name -> count (new format)
        total_messages: Total number of messages
        **legacy_kwargs: Backward compatibility for count, right_count
    """
    if not api_url:
        return False

    try:
        data = {"day": date_str}

        # New format: patterns as flat fields
        if patterns_dict:
            data.update(patterns_dict)

        # Legacy format support
        if "count" in legacy_kwargs:
            data["count"] = legacy_kwargs["count"]
        if "right_count" in legacy_kwargs:
            data["right_count"] = legacy_kwargs["right_count"]

        if total_messages is not None:
            data["total_messages"] = total_messages
        if secret:
            data["secret"] = secret

        req = urllib.request.Request(
            f"{api_url}/api/set",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            response_text = response.read().decode("utf-8")
            if response.status == 200:
                log_upload(api_url, data, "success", response_text)
                return True
            elif response.status == 401:
                log_upload(api_url, data, "unauthorized")
                print(f"\n🚫 AUTHORIZATION FAILED!")
                print(f"   Check your secret key and try again.")
                return "STOP"
            else:
                log_upload(api_url, data, f"error_http_{response.status}")
                print(f"  API error for {date_str}: {response.status}")
                return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            log_upload(api_url, data, "unauthorized", error=e)
            print(f"\n🚫 AUTHORIZATION FAILED!")
            print(f"   Check your secret key and try again.")
            return "STOP"
        else:
            log_upload(api_url, data, f"error_http_{e.code}", error=e)
            print(f"  API error for {date_str}: HTTP {e.code}")
            return False
    except Exception as e:
        log_upload(api_url, data, "error_exception", error=e)
        print(f"  API error for {date_str}: {e}")
        return False


def process_message_entry(entry, compiled_patterns):
    """
    Process a single JSONL entry and extract message info + pattern matches.

    Returns dict with:
        - msg_id: The message UUID
        - date_str: Date in YYYY-MM-DD format
        - text_blocks: List of (text, matched_patterns) tuples
    Returns None if entry should be skipped.
    """
    if entry.get("type") != "assistant":
        return None

    msg_id = entry.get("uuid") or entry.get("requestId")
    if not msg_id:
        return None

    # Parse timestamp
    timestamp = entry.get("timestamp", "")
    if timestamp:
        entry_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        date_str = entry_time.strftime("%Y-%m-%d")
    else:
        date_str = get_utc_today()

    # Extract text blocks and check for pattern matches
    text_blocks = []
    message = entry.get("message", {})
    if "content" in message:
        for content_item in message.get("content", []):
            if isinstance(content_item, dict) and content_item.get("type") == "text":
                text = content_item.get("text", "")

                # Check for pattern matches
                matched_patterns = {}
                for pattern_name, pattern_regex in compiled_patterns.items():
                    if pattern_regex.search(text):
                        matched_patterns[pattern_name] = True

                text_blocks.append((text, matched_patterns))

    return {
        "msg_id": msg_id,
        "date_str": date_str,
        "text_blocks": text_blocks,
    }


def get_project_display_name(project_dir_name):
    name = project_dir_name
    for prefix in ["-Users-", "-home-", "-var-"]:
        if name.startswith(prefix):
            parts = name.split("-", 3)
            if len(parts) > 3:
                name = parts[3]
            break
    return name


def get_utc_today():
    """Get today's date in UTC (same format as JSONL timestamps)"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
